""" 知识库问答请求和响应模型 """
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.db.models import Message

MessageRoleValue = Literal["user", "assistant", "system"]
QueryRouteValue = Literal["original", "rewrite", "hyde", "multi_query"] # 定义4个路由策略
AgentActionValue = Literal["initial", "proceed", "rewrite_query", "switch_route", "refuse"]

""" Agent的RAG单轮决策和观察快照 """
class AgentStep(BaseModel):
    round: int
    action: AgentActionValue
    reason: str
    route: QueryRouteValue
    query: str
    retrieved_count: int | None = None
    top_score: float | None = None
    sufficient: bool | None = None

# Query查询优化的调试快照，仅assistant消息会带，前端用于渲染面板
class QueryRouteRead(BaseModel):
    route: QueryRouteValue
    query: str
    rewritten_query: str | None = None
    hyde_answer: str | None = None
    multi_queries: list[str] | None = None


# 创建对话请求体
class ConversationCreate(BaseModel):
    title: str = Field("新对话", max_length=256, min_length=1)

# 读取对话响应体
class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

# 混合检索调试的元数据 - 用于前端展示
class RetrievalMeta(BaseModel):
    sources: list[str] = Field(default_factory=list)
    vector_rank: int | None = None
    vector_score: float | None = None
    keyword_rank: int | None = None
    keyword_score: float | None = None
    rrf_score: float | None = None

# 知识库引用的chunk快照
class CitationRead(BaseModel):
    id: UUID
    ordinal: int # 引用序号
    chunk_id: UUID | None = None
    document_id: UUID | None = None
    document_name: str
    page_no: int | None = None
    quote: str
    retrieval_meta: RetrievalMeta | None = None # 混合检索源数据

    @classmethod
    def from_orm(cls, citation) -> "CitationRead":
        return cls(
            id=citation.id,
            ordinal=citation.ordinal,
            chunk_id=citation.chunk_id,
            document_id=citation.document_id,
            document_name=citation.document_name,
            page_no=citation.page_no,
            quote=citation.quote,
            retrieval_meta=parse_retrieval_meta(citation.retrieval_meta)
        )

# 解析混合检索元数据, 由于这是添加的字段，历史消息没有RetrievalMeta,缺失返回空
def parse_retrieval_meta(raw: dict | None) -> RetrievalMeta | None:
    if not isinstance(raw, dict):
        return None
    try:
        return RetrievalMeta.model_validate(raw)
    except Exception:
        return None

# 消息体
class MessageRead(BaseModel):
    id: UUID
    role: MessageRoleValue
    content: str
    created_at: datetime
    citations: list[CitationRead] = Field(default_factory=list)
    query_route: QueryRouteRead | None = None
    agent_steps: list[AgentStep] | None = None # Agent 2G决策

    @classmethod
    def from_orm(cls, message) -> "MessageRead":
        is_assistant = message.role == "assistant"
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            citations=[CitationRead.from_orm(c) for c in message.citations]
            if is_assistant
            else [],
            query_route= _parse_query_route(message.extra_metadata)
            if is_assistant
            else None,
            agent_steps=_parse_agent_steps(message.extra_metadata)
            if is_assistant else None,
        )

""" 从Message extra metadata解析Agent Steps缺失返回空 """
def _parse_agent_steps(metadata: dict | None) -> list[AgentStep] | None:
    if not metadata:
        return None
    raw = metadata.get("agent_steps")
    if not isinstance(raw, list) or not raw:
        return None
    parsed: list[AgentStep] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        try:
            parsed.append(AgentStep.model_validate(item))
        except Exception:
            return None
    return parsed

# 从Meta metadata中提取query route字段
def _parse_query_route(metadata: dict | None) -> QueryRouteRead | None:
    if not metadata:
        return None
    raw = metadata.get("query_route")
    if not isinstance(raw, dict):
        return None
    try:
        return QueryRouteRead.model_validate(raw)
    except Exception:
        return None

# 对话详情
class ConversationDetail(BaseModel):
    conversation: ConversationRead
    messages: list[MessageRead]

# 知识库问答请求体
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
