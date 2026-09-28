""" 定义文档相关的请求和响应模型:通过Pydantic Schemas """
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.services import document_service

DocumentStatusValue = Literal["uploading", "parsing", "indexing", "ready", "failed"]

""" 文档列表 """
# 文档列表项
class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    file_hash: str
    mime_type: str
    size: int
    status: DocumentStatusValue
    error_message: str | None
    created_at: datetime
    updated_at: datetime

# 文档列表响应
class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

""" Chunk列表 """
_CONTENT_EXCERPT_LIMIT = 100

# Chunk列表项
class DocumentChunkRead(BaseModel):
    id: UUID
    chunk_index: int
    page_no: int | None = None
    section_path: str | None = None
    content_excerpt: str
    char_count: int
    chunk_hash: str

    @classmethod
    def from_orm_chunk(cls, chunk) -> "DocumentChunkRead":
        content = chunk.content or ""
        excerpt = content[:_CONTENT_EXCERPT_LIMIT]
        if len(content) > _CONTENT_EXCERPT_LIMIT:
            excerpt += "..."
        return cls(
            id=chunk.id,
            chunk_index=chunk.chunk_index,
            page_no=chunk.page_no,
            section_path=chunk.section_path,
            content_excerpt=excerpt,
            char_count=len(content),
            chunk_hash=chunk.chunk_hash
        )

# 切分统计
class DocumentChunkStats(BaseModel):
    total: int
    avg_length: int
    min_length: int
    max_length: int

# chunk响应列表
class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkRead]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    stats: DocumentChunkStats | None = None

""" Chunk详情: 返回完整Content """

class DocumentChunkDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    page_no: int | None = None
    section_path: str | None = None
    content: str
    char_count: int
    chunk_hash: str
    created_at: datetime

    @classmethod
    def from_orm_chunk(cls, chunk) -> "DocumentChunkDetail":
        return cls(
            id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            page_no=chunk.page_no,
            section_path=chunk.section_path,
            content=chunk.content,
            char_count=len(chunk.content or ""),
            chunk_hash=chunk.chunk_hash,
            created_at=chunk.created_at,
        )

