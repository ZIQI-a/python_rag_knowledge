""" 文档的数据库层操作 """
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentStatus


class DocumentRepository:

    # 构造函数初始化
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 根据ID获取文档
    async def get_by_id(self, document_id: UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    # 根据hash获取文档
    async def get_by_hash(self, file_hash: str) -> Document | None:
        return (await self.session.execute(
            select(Document).where(Document.file_hash == file_hash)
        )).scalar_one_or_none()

    # 新增文档
    async def add(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        return document

    # 更新文档状态
    async def update_status(self, document_id: UUID, status: DocumentStatus, *,
                            error_message: str | None = None) -> Document | None:
        """读取并更新文档状态，文档不存在时返回 None。"""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None
        doc.status = status
        if error_message is not None or status != DocumentStatus.FAILED:
            doc.error_message = error_message
        return doc

    # 删除指定的文档
    async def delete(self, document: Document) -> None:
        return await self.session.delete(document)

    # 查看文档的列表
    async def list_paginated(self, page: int, page_size: int, *, status: DocumentStatus | None = None):
        offset = (page - 1) * page_size
        item_stmt = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(Document)
        if status is not None:
            item_stmt = item_stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)

        items = (await self.session.execute(item_stmt)).scalars().all()
        total_count = (await self.session.execute(count_stmt)).scalar_one()
        return list(items), int(total_count)
