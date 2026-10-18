""" 知识库问答请求和响应模型 """
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.core.observbility import build_trace_url

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

# 对话详情
class ConversationDetail(BaseModel):
    conversation: ConversationRead
    messages: list[MessageRead]

# 知识库问答请求体
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

""" 会话展示， 列表 """
# 会话列表元素侧栏渲染
class ConversationListItem(BaseModel):
    id: UUID
    title: str
    updated_at: datetime
    message_count: int

# 会话列表分页响应
class ConversationPage(BaseModel):
    items: list[ConversationListItem]
    total: int
    page: int
    page_size: int

# 读取验证结果
class VerifyResultRead(BaseModel):
    verified: bool
    reason: str | None = None


# 创建对话请求体
class ConversationCreate(BaseModel):
    title: str = Field("新会话", max_length=256, min_length=1)

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
    rerank_score: float | None = None

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
    verify_result: VerifyResultRead | None = None
    trace_id: str | None = None
    trace_url: str | None = None
    cache_hit: bool = False

    @classmethod
    def from_orm(cls, message) -> "MessageRead":
        is_assistant = message.role == "assistant"
        trace_id = _parse_trace_id(message.extra_metadata) if is_assistant else None
        cache_hit = _parse_cache_hit(message.extra_metadata) if is_assistant else False,
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
            verify_result=_parse_verify_result(message.extra_metadata)
            if is_assistant else None,
            trace_id=trace_id,
            trace_url=build_trace_url(trace_id),
            cache_hit=cache_hit,
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
# 解析大模型校验结果
def _parse_verify_result(metadata: dict | None) -> VerifyResultRead | None:
    if not metadata:
        return None
    raw = metadata.get("verify_result")
    if not isinstance(raw, dict):
        return None
    try:
        return VerifyResultRead.model_validate(raw)
    except Exception:
        return None


# 从meta data中解析出trace id
def _parse_trace_id(metadata: dict | None) -> str | None:
    if not metadata:
        return None
    raw = metadata.get("trace_id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw

def _parse_cache_hit(metadata: dict | None) -> bool:
    """从 messages.extra_metadata 中提取 cache_hit 标记。

    历史消息没有该字段，按 False 处理。
    """
    if not metadata:
        return False
    raw = metadata.get("cache_hit")
    return bool(raw)