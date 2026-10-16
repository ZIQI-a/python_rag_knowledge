""" 分片chunk数据的增删改查操作 """
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import DocumentChunk, Document

# 通配权限标签：admin 角色持有，含义"无视权限过滤"
WILDCARD_PERMISSION_TAG = "*"

# 构造文档可见性的公共WHERE条件，供 document_repo 与检索查询复用
def _permission_where(permission_tags: list[str] | None) -> ColumnElement[bool] | None:
    """构造文档可见性 WHERE 条件。

    - None：调用方（评测 / 启动期种子）显式不限制
    - 含 "*"：admin 通配，不加条件
    - 其他：'空权限标签视为公开' OR '数组重叠'
    """
    if permission_tags is None:
        return None
    if WILDCARD_PERMISSION_TAG in permission_tags:
        return None
    return or_(
        func.cardinality(Document.permission_tags) == 0,
        Document.permission_tags.op("&&")(permission_tags),
    )


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

    # 向量搜索(基于余弦距离向量相似度)
    async def vector_search(self, query_embedding: list[float], top_k: int
                            ) -> list[tuple[DocumentChunk, float]]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(DocumentChunk, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.status == 'ready')
            .order_by(distance.asc())
            .limit(top_k)
            .options(selectinload(DocumentChunk.document))
        )
        rows = (await self.session.execute(stmt)).all()
        return [(chunk, float(dist)) for chunk, dist in rows]

    # 基于关键词搜索(全文中文检索)
    async def keyword_search(self, query: str, top_k: int) -> list[tuple[DocumentChunk, float]]:
        # 使用Chinese_zh文本搜索配置
        tsquery = func.plainto_tsquery("chinese_zh", query)
        rank_expr = func.ts_rank(DocumentChunk.content_tsv, tsquery)
        stmt = (
            select(DocumentChunk, rank_expr.label("rank"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                # 必须是已就绪状态
                Document.status == "ready",
                DocumentChunk.content_tsv.op("@@")(tsquery),
            )
            .order_by(rank_expr.desc())
            .limit(top_k)
            .options(selectinload(DocumentChunk.document))
        )
        rows = (await self.session.execute(stmt)).all()
        return [(chunk, float(rank)) for chunk, rank in rows]


