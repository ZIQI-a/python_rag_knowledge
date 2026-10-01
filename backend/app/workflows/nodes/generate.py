""" 流式逐token生成内容 """
from collections.abc import AsyncIterator

from app.llm.models import get_chat_model
from app.llm.prompts import build_answer_messages
from app.workflows.rag_state import RAGState

# 流式生成节点
async def stream_generate(state: RAGState) -> AsyncIterator[str]:
    messages = build_answer_messages(
        question=state["question"],
        chunks=state["retrieved_chunks"],
        history=state.get("chat_history", []),
    )
    async for chunk in get_chat_model().astream(messages):
        text = chunk.content
        if not text:
            continue
        if isinstance(text, str):
            yield text
        else:
            yield "".join(part.get("text", "") for part in text if isinstance(part, dict))
