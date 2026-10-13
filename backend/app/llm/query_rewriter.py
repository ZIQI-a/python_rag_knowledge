""" 路由Query查询策略优化后的统一返回结果 """
from dataclasses import dataclass
import re
from typing import get_args

from app.core.logging import get_logger
from app.db.models import Message, MessageRole
from app.llm.models import get_chat_model
from app.llm.prompts import build_route_messages, build_rewrite_messages, build_hyde_messages, \
    build_multi_query_messages, build_contextualize_messages
from app.workflows.rag_state import QueryRoute

logger = get_logger(__name__)

_VALID_ROUTES: tuple[str, ...] = get_args(QueryRoute)

# 路由查询策略优化后的统一返回结果
@dataclass(frozen=True)
class QueryRouteResult:
    route: QueryRoute
    query: str
    rewritten_query: str | None = None
    hyde_answer: str | None = None
    multi_queries: list[str] | None = None


class QueryRewriter:

    # 决策查询路由
    async def decide_route(self, question: str) -> QueryRoute:
        messages = build_route_messages(question)
        response = await get_chat_model().ainvoke(messages)
        raw = _extract_text(response.content).strip().lower()
        token = raw.strip("\"'`.。 ")
        if token in _VALID_ROUTES:
            return token
        logger.warning("query route模型返回非法值,降级 original: raw=%r",raw)
        return "original"
    # 重写查询模型返回
    async def rewrite(self, question: str) -> str:
        messages = build_rewrite_messages(question)
        response = await get_chat_model().ainvoke(messages)
        return _extract_text(response.content).strip()

    # 假设问题查询模型返回
    async def hyde(self, question: str) -> str:
        messages = build_hyde_messages(question)
        response = await get_chat_model().ainvoke(messages)
        return _extract_text(response.content).strip()

    # 多角度查询模型返回
    async def multi_query(self, question: str, n: int) -> list[str]:
        messages = build_multi_query_messages(question, n)
        response = await get_chat_model().ainvoke(messages)
        text = _extract_text(response.content)
        # 仅移除列表前缀，保留查询中的年份、编号和末尾数字。
        queries = [
            re.sub(r"^(?:[-•*]\s+|\d+[.、)]\s+)", "", line.strip()).strip()
            for line in text.splitlines()
        ]
        return [q for q in queries if q][:n]

    """ 已知目标Router时，按Router填写对应的返回参数(在Agent的RAG切换路由时调用直接指定Route) """
    async def apply_route(
            self, question: str, route: QueryRoute, multi_query_count: int
    ) -> QueryRouteResult:
        try:
            if route == "rewrite":
                rewritten = await self.rewrite(question)
                if not rewritten:
                    return QueryRouteResult(route="original", query=question)
                return QueryRouteResult(
                    route="rewrite", query=rewritten, rewritten_query=rewritten
                )
            if route == "hyde":
                hyde_answer = await self.hyde(question)
                if not hyde_answer:
                    return QueryRouteResult(route="original", query=question)
                # 假设答案用于向量召回，原问题仍保留给最终回答节点。
                return QueryRouteResult(
                    route="hyde", query=hyde_answer, hyde_answer=hyde_answer
                )
            if route == "multi_query":
                queries = await self.multi_query(question, multi_query_count)
                if len(queries) < 2:
                    return QueryRouteResult(route="original", query=question)
                return QueryRouteResult(
                    route="multi_query", query=question, multi_queries=queries
                )
            return QueryRouteResult(route="original", query=question)
        except Exception as e:
            logger.exception("apply route模型调用失败,降级 original: e=%r ,question=%r", e, question)
            return QueryRouteResult(route="original", query=question)

    """ 基于多轮会话历史，将当前会话和问题改写为完整独立句 """
    async def contextualize(self, question: str, history: list[Message]) -> str:

        history_text = _format_history_text(history) # 列表转为字符串
        if not history_text:
            return question
        try:
            messages = build_contextualize_messages(question=question, history=history_text)
            response = await get_chat_model().ainvoke(messages)
            rewritten = _extract_text(response.content).strip()
            return rewritten or question
        except Exception:
            logger.exception(
                "上下文会话调用失败，只发送当前问题: question=%r", question
            )
            return question



    """ 统一入口 """
    async def optimize(self, question: str, multi_query_count: int) -> QueryRouteResult:
        try:
            route = await self.decide_route(question)
        except Exception as e:
            logger.exception("query optimize模型调用失败,降级 original: e=%r ,question=%r",e, question)
            return QueryRouteResult(route="original", query=question)
        return await self.apply_route(question, route, multi_query_count)

_rewriter: QueryRewriter | None = None

# 封装单例
def get_query_rewriter() -> QueryRewriter:
    global _rewriter
    if _rewriter is None:
        _rewriter = QueryRewriter()
    return _rewriter

def _extract_text(content: str | list[str | dict]) -> str:
    """ 兼容Langchain ChatModel的Content联合类型 """
    if isinstance(content, str):
        return content
    # 兼容字符串片段和文本块，避免字符串列表被丢弃后误降级。
    return "".join(
        part if isinstance(part, str) else part.get("text", "")
        for part in content
        if isinstance(part, (str, dict))
    )

_ROLE_LABEL: dict[MessageRole, str] = {
    MessageRole.USER: "用户",
    MessageRole.ASSISTANT: "AI",
    MessageRole.SYSTEM: "系统"
}

# 将历史消息列表转为字符串,给AI方便查看
def _format_history_text(history):
    lines: list[str] = []
    for msg in history:
        role_label = _ROLE_LABEL.get(msg.role)
        if not role_label or not msg.content.strip():
            continue
        lines.append(f"{role_label}: {msg.content.strip()}")
    return "\n".join(lines)