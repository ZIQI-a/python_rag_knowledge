""" 分片chunk数据的增删改查操作 """
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk


# 单个文档下的chunk长度统计
# 全域空表示文档没有任何内容
@dataclass(frozen=True)
class ChunkStats:
    total: int
    avg_length: int
    min_length: int
    max_length: int


class DocumentChunkRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    # 添加文档chunk列表
    async def bulk_add(self, chunks: Sequence[DocumentChunk]) -> None:
        if chunks is None:
            return
        self.session.add_all(chunks)
        await self.session.flush()

    # 删除给定的文档Chunk内容
    async def delete_by_document(self, document_id: UUID) -> None:
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        await self.session.execute(stmt)

    # 展示文档列表
    async def list_paginated_by_document(self, document_id: UUID, page: int, page_size: int
                                         ) -> tuple[list[DocumentChunk], int]:
        # 设置偏移，确保页数和内容匹配
        offset = (page - 1) * page_size
        # 查询分页数据
        items_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .offset(offset)
            .limit(page_size)
        )
        # 查询总数
        count_stmt = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        items = (await self.session.execute(items_stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(items), int(total)

    # 获取指定的文档数据
    async def get_for_document(self,
                               document_id: UUID, chunk_id: UUID
                               ) -> DocumentChunk | None:
        """按 document_id + chunk_id 双条件查询。
        强校验归属，避免拿 A 文档的 id 越权读 B 文档的 chunk。
        """
        stmt = select(DocumentChunk).where(
            DocumentChunk.id == chunk_id, DocumentChunk.document_id == document_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_status(self, document_id: UUID) -> ChunkStats | None:
        length = func.char_length(DocumentChunk.content)
        stmt = (
            select(
                func.count().label("total"),
                func.avg(length).label("avg_len"),
                func.min(length).label("min_len"),
                func.max(length).label("max_len")
            ).where(DocumentChunk.document_id == document_id)
        )
        row = (await self.session.execute(stmt)).one()
        if not row.total:
            return None
        return ChunkStats(
            total=int(row.total),
            avg_length=int(row.avg_len or 0),
            min_length=int(row.min_len or 0),
            max_length=int(row.max_len or 0)
        )
