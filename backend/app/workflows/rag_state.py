""" 搭建LangGraph节点流，问答链拆成多个节点 """
from typing import TypedDict, Literal
from uuid import UUID

from app.db.models import Message
from app.retrieval.vector_retriever import RetrievedChunk

# 4种查询路由策略，原始查询、重写、假设查询、多角度查询
QueryRoute = Literal["original", "rewrite", "hyde", "multi_query"]

# RAG 状态
# `TypedDict(total=False)` 表示每个字段都是可选的
class RAGState(TypedDict, total=False):
    # 输入
    conversation_id: UUID
    question: str

    chat_history: list[Message]
    query: str

    route: QueryRoute
    rewritten_query: str |None # 重写查询
    hyde_answer: str | None # 假设答案查询
    multi_queries: list[str] | None

    retrieved_chunks: list[RetrievedChunk]
    refused: bool # 是否触发拒答，True跳过generate
    # Agentic RAG循环
    agent_steps: list[str]
    retrieval_round: int
    # 判断本轮候选是否足够，为True走向end
    context_sufficient: bool
    # Rerank基于Top一分数的拒答;False走向拒绝节点True走向End
    context_is_enough: bool
    # generate
    answer: str

    user_message_id: UUID
    assistant_message_id: UUID
    # trace id
    trace_id: str | None

