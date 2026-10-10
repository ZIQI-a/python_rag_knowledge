from app.llm.query_rewriter import get_query_rewriter
from app.workflows.rag_state import RAGState


async def normalize_query(state: RAGState) -> RAGState:
    history = state.get("chat_history") or []
    if not history:
        return {"query": state["question"]}
    # 如果有历史的话，将历史消息和当前问题一并给AI进行结合分析
    rewritten = await get_query_rewriter().contextualize(
        question=state["question"], history=history
    )
    return {"query": rewritten}

