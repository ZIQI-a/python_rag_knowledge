""" 问答流程 """
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import UUID

import time
from langsmith import traceable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.observbility import get_current_trace_id, build_trace_url
from app.db.models import Conversation, Message, AnswerCitation
from app.db.repositories.citation_repo import AnswerCitationRepository
from app.db.repositories.conversation_repo import ConversationRepository
from app.db.session import AsyncSessionLocal
from app.llm.answer_verifier import VerifyResult, get_answer_verifier
from app.llm.prompts import REFUSAL_ANSWER
from app.retrieval.vector_retriever import RetrievedChunk
from app.workflows.graph import get_rag_graph
from app.workflows.nodes import load_context, stream_generate
from app.workflows.rag_state import RAGState

# 导入日志模块
logger = get_logger(__name__)


# 将检索结果序列化成JSON
def _serialize_citation(chunk: RetrievedChunk, ordinal: int) -> dict:
    return {
        "ordinal": ordinal,
        "chunk_id": str(chunk.chunk_id),
        "document_id": str(chunk.document_id),
        "document_name": chunk.document_name,
        "page_no": chunk.page_no,
        "section_path": chunk.section_path,
        "score": round(chunk.score, 4),
        "quote": chunk.content,
        "retrieval_meta": _build_retrieval_meta(chunk)
    }


# SSE\metadata共用的query router荷载格式
def _build_query_route_payload(state: RAGState) -> dict:
    return {
        "route": state.get("route", "original"),
        "query": state.get("query", ""),
        "rewritten_query": state.get("rewritten_query"),
        "hyde_answer": state.get("hyde_answer"),
        "multi_queries": state.get("multi_queries"),
    }


# 混合检索调试元数据的展示
def _build_retrieval_meta(chunk: RetrievedChunk) -> dict:
    return {
        "sources": list(chunk.sources),
        "vector_rank": chunk.vector_rank,
        "vector_score": round(chunk.vector_score, 4) if chunk.vector_score is not None else None,
        "keyword_rank": chunk.keyword_rank,
        "keyword_score": round(chunk.keyword_score, 4) if chunk.keyword_score is not None else None,
        "rrf_score": (
            # 保留6位本身很小，保留4位会丢精度
            round(chunk.rrf_score, 6) if chunk.rrf_score is not None else None
        ),
        "rerank_score": (
            round(chunk.rerank_score, 4) if chunk.rerank_score is not None else None
        )
    }


# 答案输出后，认证校验的核载构造; SSE/metadata共用核载
def _build_verify_payload(
        result: VerifyResult, *, replacement_answer: str | None
) -> dict:
    payload: dict = {
        "verified": result.verified,
        "reason": result.reason or None
    }
    # replacement_answer仅在非认证时携带，替换展示答案
    if not result.verified and replacement_answer is not None:
        payload["replacement_answer"] = replacement_answer
    return payload


""" SSE和Meta共用的核载形式 """
def _serialize_agent_steps(state: RAGState) -> list[dict]:
    return [dict(step) for step in state.get("agent_steps", [])]


""" 评测专用 """

@dataclass(frozen=True)
class EvaluationAnswer:
    """ 评测专用，跑一遍RAG拿到非流式的Answer结果;不写入数据库，与正常流式输出的答案不同 """
    answer: str
    refused: bool
    chunks: list[RetrievedChunk]
    query_route: dict
    agent_steps: list[dict]
    verify_result: VerifyResult | None
    trace_id: str | None
    latency_ms: int
    first_token_latency_ms: int | None
    error_message: str | None = None
    citations: list[dict] = field(default_factory=list)

class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 创建新对话
    async def create_conversation(self, title: str = "新会话") -> Conversation:
        repo = ConversationRepository(self.session)
        conversation = await repo.create(title=title)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    # 获取对话
    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        repo = ConversationRepository(self.session)
        conversation = await repo.get(conversation_id)
        if conversation is None:
            raise NotFoundError("会话不存在")
        return conversation

    # 获取对话历史消息
    async def list_messages(self, conversation_id: UUID) -> tuple[Conversation | None, list[Message]]:
        conversation = await self.get_conversation(conversation_id)
        repo = ConversationRepository(self.session)
        messages = await repo.list_message(conversation_id)
        return conversation, messages

    # 展示会话列表
    async def list_conversation(
            self, page: int, page_size: int
    ) -> tuple[list[tuple[Conversation, int]], int]:
        repo = ConversationRepository(self.session)
        return await repo.list_page(page=page, page_size=page_size)

    # 删除会话
    async def delete_conversation(self, conversation_id: UUID) -> None:
        repo = ConversationRepository(self.session)
        deleted = await repo.delete(conversation_id)
        if not deleted:
            raise NotFoundError("会话不存在")
        await self.session.commit()

    """ 流式输出回答，主要方案 """

    @traceable(name="ChatService.stream_answer", run_type="chain")
    async def stream_answer(self,
                            conversation_id: UUID, question: str) -> AsyncIterator[dict]:
        """逐事件 yield SSE 载荷。

        事件协议（与前端约定）：
            message_start → query_route → agent_steps → citations → token...
            → [verify_result] → message_end
        - 拒答路径不发 verify_result（拒答本身已经是终态）
        - verify_result.verified=False 时携带 replacement_answer，前端按它整段
          替换流式出来的答案，与 PRD"校验失败 → 拒答替换"对齐
        任何阶段出错则改 yield error 并提前结束。
        """
        await self.get_conversation(conversation_id)

        async with AsyncSessionLocal() as session:
            try:
                trace_id = get_current_trace_id()
                state: RAGState = {
                    "conversation_id": conversation_id,
                    "question": question,
                    "trace_id": trace_id
                }

                # 1 加载上下文（仅历史消息), 加载路由
                state.update(await load_context(state, session))

                # 2 跑RAG子图
                final_state = await get_rag_graph().ainvoke(state)
                state.update(final_state)
                # 3 用户的消息写入数据库
                await self._persist_user_message(state, session)

                yield {
                    "event": "message_start",
                    "data": {"user_message_id": str(state["user_message_id"]),
                             "trace_id": trace_id,
                             "trace_url": build_trace_url(trace_id)},
                }
                # 把query流结果推送到前端,前端通过Router选择
                yield {
                    "event": "query_route",
                    "data": _build_query_route_payload(state)
                }
                # Agent step事件
                yield {
                    "event": "agent_steps",
                    "data": {"steps": _serialize_agent_steps(state)}
                }

                # 4 retrieve,搜索分析含距达判定，先把引用放在前端，让资料面板可见
                citations_payload = (
                    []
                    if state.get("refused")
                    else [
                        _serialize_citation(c, ordinal=i)
                        for i, c in enumerate(state.get("retrieved_chunks", []), start=1)
                    ]
                )
                yield {
                    "event": "citations",
                    "data": {"citations": citations_payload},
                }

                # 5 生成，如果拒绝则输出拒绝文案
                verify_result: VerifyResult | None = None
                if state.get("refused"):
                    yield {
                        "event": "token",
                        "data": {"delta": state["answer"]},
                    }
                else:
                    answer_parts: list[str] = []
                    async for delta in stream_generate(state):
                        answer_parts.append(delta)
                        yield {"event": "token", "data": {"delta": delta}}
                    state["answer"] = "".join(answer_parts)

                    # 6 最终答案llm校验(认证仅在不拒答情况下执行，因为拒答情况下已经有现成的拒答文案)
                    if settings.verify_answer_enabled:
                        # 校验针对用户原问题，避免将 HyDE 假设答案当成问题。
                        verify_result = await get_answer_verifier().verify(
                            question=state["question"],
                            answer=state["answer"],
                            chunks=list(state.get("retrieved_chunks", []))
                        )
                        replacement = (
                            REFUSAL_ANSWER if not verify_result.verified else None
                        )
                        if not verify_result.verified:
                            state["answer"] = REFUSAL_ANSWER
                            state["refused"] = True
                        yield {
                            "event": "verify_result",
                            "data": _build_verify_payload(
                                verify_result, replacement_answer=replacement
                            ),
                        }

                # 6 AI消息+引用写入数据库
                await self._persist_assistant_message(state, session, verify_result=verify_result)
                yield {
                    "event": "message_end",
                    "data": {
                        "message_id": str(state["assistant_message_id"]),
                        "refused": bool(state.get("refused"))
                    },
                }
            except Exception as exc:
                logger.exception("Chat stream failed: conversation_id = %s", conversation_id)
                await session.rollback()
                yield {
                    "event": "error",
                    "data": {
                        "code": "chat_stream_failed",
                        "message": str(exc).strip() or "问答处理失败",
                    }
                }

    """ 写入用户消息(流式开始前 """

    async def _persist_user_message(
            self, state: RAGState, session: AsyncSession
    ) -> None:
        repo = ConversationRepository(session)
        # 如果是首次提问，会话还没有任何消息，将标题改为本次问题
        if await repo.count_messages(state["conversation_id"]) == 0:
            await repo.update_title_if_default(
                state["conversation_id"], state["question"]
            )
        user_msg = ConversationRepository.make_user_message(
            state['conversation_id'], content=state["question"]
        )
        await repo.add_message([user_msg])
        await session.commit()
        state["user_message_id"] = user_msg.id

    """ 写入AI消息(流式结束后 """

    async def _persist_assistant_message(
            self, state: RAGState, session: AsyncSession, *, verify_result: VerifyResult | None
    ) -> None:
        conv_repo = ConversationRepository(session)
        citation_repo = AnswerCitationRepository(session)

        extra_metadata = {
            "refused": bool(state.get("refused")),
            "query_route": _build_query_route_payload(state),
            "agent_steps": _serialize_agent_steps(state),
            "trace_id": state.get("trace_id")
        }
        if verify_result is not None:
            extra_metadata["verify_result"] = _build_verify_payload(
                verify_result, replacement_answer=None
            )

        assistant_msg = ConversationRepository.make_assistant_message(
            state["conversation_id"],
            content=state["answer"],
            # 把query流结果持久化到meta data字段，即使刷新时前端还能继续展示
            extra_metadata=extra_metadata
        )
        await conv_repo.add_message([assistant_msg])

        if not state.get("refused"):
            citations = [
                AnswerCitation(
                    message_id=assistant_msg.id,
                    ordinal=ordinal,
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    document_name=chunk.document_name,
                    page_no=chunk.page_no,
                    quote=chunk.content,
                    retrieval_meta=_build_retrieval_meta(chunk)
                )
                for ordinal, chunk in enumerate(
                    state.get("retrieved_chunks", []), start=1
                )
            ]
            await citation_repo.bulk_add(citations)
        await session.commit()
        state["assistant_message_id"] = assistant_msg.id

    """ 跑一遍完整RAG流程，拿非流式结果用于评测 """
    @traceable(name="ChatService.answer_for_evaluation", run_type="chain")
    async def answer_for_evaluation(self, question: str) -> EvaluationAnswer:
        started_at = time.perf_counter()
        trace_id = get_current_trace_id()
        state: RAGState = {
            "conversation_id": UUID(int=0),
            "question": question,
            "chat_history": [],
            "trace_id": trace_id
        }

        try:
            final_state = await get_rag_graph().ainvoke(state)
            state.update(final_state)

            verify_result: VerifyResult | None = None
            first_token_latency_ms: int | None = None

            if state.get("refused"):
                answer = state["answer"]
            else:
                parts: list[str] = []
                async for delta in stream_generate(state):
                    if first_token_latency_ms is None:
                        first_token_latency_ms = int(
                            (time.perf_counter() - started_at) * 1000
                        )
                    parts.append(delta)
                answer = "".join(parts)
                state["answer"] = answer
                # 进入认证，只有不拒绝的情况下才认证
                if settings.verify_answer_enabled:
                    verify_result = await get_answer_verifier().verify(
                        question=question,
                        answer=answer,
                        chunks=list(state.get("retrieved_chunks", []))
                    )
                    if not verify_result.verified:
                        answer = REFUSAL_ANSWER
                        state["answer"] = answer
                        state["refused"] = True

            chunks = list(state.get("retrieved_chunks", []))
            refused = bool(state.get("refused"))
            citations = (
                []
                if refused else [_serialize_citation(c, ordinal=i) for i, c in enumerate(chunks, 1)]
            )

            return EvaluationAnswer(
                answer=answer,
                refused=refused,
                chunks=chunks,
                query_route=_build_query_route_payload(state),
                agent_steps=_serialize_agent_steps(state),
                verify_result=verify_result,
                trace_id=trace_id,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                first_token_latency_ms=first_token_latency_ms,
                citations=citations
            )

        except Exception as e:
            logger.exception("评测答案失败: question=%r", question)
            return EvaluationAnswer(
                answer="",
                refused=False,
                chunks=[],
                query_route=_build_query_route_payload(state),
                agent_steps=_serialize_agent_steps(state),
                verify_result=None,
                trace_id=trace_id,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                first_token_latency_ms=None,
                error_message=str(e).strip() or e.__class__.__name__
            )


