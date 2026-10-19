""" MCP工具的入参、出参模型 """
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.api.schemas.documents import DocumentStatusValue, IngestionTaskStatusValue

""" 问答相关参数 """

class MCPCitation(BaseModel):
    """ 问答引用快照: 只保留Agent需要用到的字段 """
    ordinal: int = Field(description="Pydantic中给LLM的片段n编号")
    document_id: UUID
    document_name: str
    page_no: int | None = None
    section_path: str | None = None
    quote: str = Field(description="该片段在Prompt里的原文")

class MCPAskAnswer(BaseModel):
    """ Ask knowledge base出参 """
    answer: str
    refused: bool = Field(description="是否触发拒答")
    citations: list[MCPCitation] = Field(default_factory=list)
    trace_id: str | None = Field(
        default=None, description="LangSmith trace_id,未启用时为空"
    )

""" 文档相关参数 """

class MCPUploadResult(BaseModel):
    """upload_document 出参。"""

    document_id: UUID
    name: str
    status: DocumentStatusValue
    version: int
    file_hash: str = Field(
        description="sha256；文件级幂等键，相同 hash 复用现有文档"
    )

class MCPDocumentItem(BaseModel):
    """list_documents 列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: DocumentStatusValue
    mime_type: str
    size: int
    version: int
    permission_tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class MCPDocumentList(BaseModel):
    """list_documents 出参，标准分页结构。"""

    items: list[MCPDocumentItem]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

class MCPDocumentStatus(BaseModel):
    """get_document_status 出参。
    """

    document_id: UUID
    name: str
    status: DocumentStatusValue
    version: int
    error_message: str | None = None
    latest_task_type: Literal["ingest", "reindex"] | None = None
    latest_task_status: IngestionTaskStatusValue | None = None
    latest_task_progress_total: int | None = None
    latest_task_progress_done: int | None = None
    latest_task_error_message: str | None = None

class MCPStats(BaseModel):
    """get_knowledge_base_stats 出参。

    严格按调用者权限范围统计；admin 视角看全量，普通用户只看自己有权访问的。
    """

    document_count: int
    chunk_count: int
    last_indexed_at: datetime | None = Field(
        default=None,
        description="最近一次进入 ready 状态的文档时间；库为空时返回 null",
    )