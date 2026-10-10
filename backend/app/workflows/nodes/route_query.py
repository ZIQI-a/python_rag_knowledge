""" 调用路由查询，选择策略节点 """
from app.core.config import settings
from app.llm.query_rewriter import get_query_rewriter
from app.workflows.rag_state import RAGState


# 判断路由查询策略开关是否打开，打开则调用策略
async def route_query(state: RAGState) -> RAGState:
    # 如果路由查询策略开关关闭，则直接返回original
    if not settings.query_route_enabled:
        return {"route": "original"}
    result = await get_query_rewriter().optimize(
        question=state["query"],
        multi_query_count=settings.multi_query_count
    )

    update: RAGState = {"route": result.route, "query": result.query}
    if result.rewritten_query is not None:
        update["rewritten_query"] = result.rewritten_query
    if result.hyde_answer is not None:
        update["hyde_answer"] = result.hyde_answer
    if result.multi_queries is not None:
        update["multi_queries"] = result.multi_queries
    return update