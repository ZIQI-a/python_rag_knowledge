""" 文档的数据库层操作 """
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Document, DocumentStatus
from app.db.repositories.chunk_repo import _permission_where


class DocumentRepository:

    # 构造函数初始化
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 根据ID获取文档
    async def get_by_id(
        self, document_id: UUID, *,
        permission_tags: list[str] | None = None,
    ) -> Document | None:
        """按 id 查文档；非 None permission_tags 时叠加可见性过滤。"""
        if permission_tags is None:
            return await self.session.get(Document, document_id)
        perm_where: ColumnElement[bool] | None = _permission_where(permission_tags)
        stmt = select(Document).where(Document.id == document_id)
        if perm_where is not None:
            stmt = stmt.where(perm_where)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    # 缓存来源的实时可见性检查
    async def all_ready_and_visible(
        self, document_ids: set[UUID], *, permission_tags: list[str]
    ) -> bool:
        """批量确认缓存涉及的全部文档仍存在、就绪且对当前用户可见。"""
        if not document_ids:
            return False
        stmt = select(func.count()).select_from(Document).where(
            Document.id.in_(document_ids),
            Document.status == DocumentStatus.READY,
        )
        perm_where = _permission_where(permission_tags)
        if perm_where is not None:
            stmt = stmt.where(perm_where)
        count = int((await self.session.execute(stmt)).scalar_one())
        return count == len(document_ids)

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
    async def list_paginated(
        self, page: int, page_size: int, *,
        status: DocumentStatus | None = None,
        permission_tags: list[str] | None = None,
    ) -> tuple[list[Document], int]:
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

        # 权限过滤：None 或含通配时不附加条件，其余按可见性过滤
        perm_where: ColumnElement[bool] | None = _permission_where(permission_tags)
        if perm_where is not None:
            item_stmt = item_stmt.where(perm_where)
            count_stmt = count_stmt.where(perm_where)

        items = (await self.session.execute(item_stmt)).scalars().all()
        total_count = (await self.session.execute(count_stmt)).scalar_one()
        return list(items), int(total_count)

    """ 
        聚合统计相关方法
    """

    async def count(
            self, *, permission_tags: list[str] | None = None,
    ) -> int:
        """ 统计可见文档总数,给MCP Get knowledge by state用 """
        stmt = select(func.count()).select_from(Document)
        perm_where = _permission_where(permission_tags) # 权限过滤
        if perm_where is not None:
            stmt = stmt.where(perm_where)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_last_indexed_at(
            self, *, permission_tags: list[str] | None = None,
    ) -> datetime | None:
        """ 获取最近一次进入Ready状态的文档时间 : 使用的是UpdateAt """
        stmt = select(func.max(Document.updated_at)).where(
            Document.status == DocumentStatus.READY
        )
        perm_where = _permission_where(permission_tags)
        if perm_where is not None:
            stmt = stmt.where(perm_where)
        return (await self.session.execute(stmt)).scalar_one_or_none()


