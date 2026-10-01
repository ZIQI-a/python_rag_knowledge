""" 搭建LangGraph节点流，问答链拆成多个节点 """
from typing import TypedDict
from uuid import UUID

from app.db.models import Message
from app.retrieval.vector_retriever import RetrievedChunk

# RAG 状态
# `TypedDict(total=False)` 表示每个字段都是可选的
class RAGState(TypedDict, total=False):
    # 输入
    conversation_id: UUID
    question: str

    chat_history: list[Message]
    query: str

    retrieved_chunks: list[RetrievedChunk]
    refused: bool # 是否触发拒答，True跳过generate
    # generate
    answer: str

    user_message_id: UUID
    assistant_message_id: UUID

