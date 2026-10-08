""" 问答流程 """
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.exceptions import NotFoundError
from app.db.models import Conversation, Message, AnswerCitation
from app.db.repositories.citation_repo import AnswerCitationRepository
from app.db.session import AsyncSessionLocal
from app.retrieval.vector_retriever import RetrievedChunk
from app.db.repositories.conversation_repo import ConversationRepository
from app.workflows.nodes import load_context, normalize_query, retrieve, stream_generate, route_query
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
    }

class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 创建新对话
    async def create_conversation(self, title: str = "新对话") -> Conversation:
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

    """ 流式输出回答，主要方案 """
    async def stream_answer(self,
                            conversation_id: UUID, question: str) -> AsyncIterator[dict]:
        await self.get_conversation(conversation_id)

        async with AsyncSessionLocal() as session:
            try:
                state: RAGState = {
                    "conversation_id": conversation_id,
                    "question": question,
                }

                # 1 加载上下文（仅历史消息), 加载路由
                state.update(await load_context(state, session))
                state.update(await normalize_query(state))
                state.update(await route_query(state))

                # 2 用户的消息写入数据库
                await self._persist_user_message(state, session)

                yield {
                    "event": "message_start",
                    "data": {"user_message_id": str(state["user_message_id"])},
                }
                # 把query流结果推送到前端,前端通过Router选择
                yield {
                    "event": "query_route",
                    "data": _build_query_route_payload(state)
                }

                # 3 retrieve,搜索分析含距达判定，先把引用放在前端，让资料面板可见
                state.update(await retrieve(state))

                citations_payload = [
                    _serialize_citation(c, ordinal=i)
                    for i, c in enumerate(state.get("retrieved_chunks", []), start=1)
                ]
                yield {
                    "event": "citations",
                    "data": {"citations": citations_payload},
                }

                # 4 生成，如果拒绝则输出拒绝文案
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
                # 5 AI消息+引用写入数据库
                await self._persist_assistant_message(state, session)
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
        user_msg = ConversationRepository.make_user_message(
            state['conversation_id'], content=state["question"]
        )
        await repo.add_message([user_msg])
        await session.commit()
        state["user_message_id"] = user_msg.id

    """ 写入AI消息(流式结束后 """
    async def _persist_assistant_message(
            self, state: RAGState, session: AsyncSession
    ) -> None:
        conv_repo = ConversationRepository(session)
        citation_repo = AnswerCitationRepository(session)

        assistant_msg = ConversationRepository.make_assistant_message(
            state["conversation_id"],
            content=state["answer"],
            # 把query流结果持久化到meta data字段，即使刷新时前端还能继续展示
            extra_metadata={
                "refused": bool(state.get("refused")),
                "query_route": _build_query_route_payload(state)
            }
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
