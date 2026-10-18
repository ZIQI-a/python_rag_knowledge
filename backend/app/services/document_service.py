""" 文档相关服务，调用定义好的下层DB操作 """
import hashlib
from collections.abc import Sequence
from pathlib import PurePath
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.models import Document, DocumentStatus, DocumentChunk, IngestionTaskType
from app.db.repositories.chunk_repo import (
    DocumentChunkRepository, ChunkStats,
)
from app.db.repositories.document_repo import DocumentRepository
from app.storage.file_service import FileService, get_file_service
from app.db.repositories.ingestion_task_repo import IngestionTaskRepository
from app.ingestion.tasks import ingest_document_task, reindex_document_task

logger = get_logger(__name__)

# 定义受支持的MIME类型
_ACCEPTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
    "text/html": ".html",
    "application/xhtml+xml": ".html"
}
# 定义支持文档的扩展名
_ACCEPTED_MIME_SUFFIXES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html"
}

# 定义删除状态白名单，在以下状态中时才可以删除
_DELETABLE_STATUSES = frozenset(
    {
        DocumentStatus.FAILED,
        DocumentStatus.READY,
        DocumentStatus.UPLOADING,
    }
)


# 规范化权限标签：去空白、去空串、去重、保持稳定顺序
def _normalize_tags(tags: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        t = tag.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


# 解析上传的文档是否符合要求，根据类型和扩展名来判断
def _resolve_mime_and_suffix(file: UploadFile) -> tuple[str, str]:
    suffix = PurePath(file.filename or "").suffix.lower()
    if suffix in _ACCEPTED_MIME_SUFFIXES:
        return _ACCEPTED_MIME_SUFFIXES[suffix], suffix

    mime = file.content_type or ""
    if mime in _ACCEPTED_MIME_TYPES:
        return mime, _ACCEPTED_MIME_TYPES[mime]

    raise ValidationError(
        f"不支持的文件类型: {file.filename}({mime or '未知'}"
        "当前仅支持PDF、DOCX、Markdown、HTML"
    )


""" 定义服务主体 """


class DocumentService:
    def __init__(self, session: AsyncSession, file_serice: FileService | None = None) -> None:
        self.session = session
        self.repo = DocumentRepository(self.session)
        self.task_repo = IngestionTaskRepository(session)
        self.chunk_repo = DocumentChunkRepository(self.session)
        self.file_service = file_serice or get_file_service()

    # 上传文档
    async def upload(
        self,
        file: UploadFile,
        *,
        created_by: UUID | None = None,
        permission_tags: Sequence[str] | None = None,
    ) -> Document:
        """一、校验文件"""
        mime_type, suffix = _resolve_mime_and_suffix(file)

        max_bytes = settings.upload_max_size_mb * 1024 * 1024
        # 多读一个字节即可识别超限文件，避免把整个大文件读入内存。
        content = await file.read(max_bytes + 1)
        if len(content) == 0:
            raise ValidationError("上传文件内容为空")
        if len(content) > max_bytes:
            raise ValidationError(f"单个文件大小不能超过: {settings.upload_max_size_mb} MB")
        # 生成哈希并查找是否存在记录
        file_hash = hashlib.sha256(content).hexdigest()

        exist = await self.repo.get_by_hash(file_hash)
        if exist is not None:
            logger.info("文件已存在: %s", exist)
            return exist

        """ 二、上传文件到COS """
        object_key = await self.file_service.upload(
            content=content, file_hash=file_hash, suffix=suffix, mime_type=mime_type
        )
        """ 三、保存文档记录到DB """
        document = Document(
            name=file.filename or f"{file_hash}{suffix}",
            file_hash=file_hash,
            mime_type=mime_type,
            size=len(content),
            storage_provider="cos",
            cos_bucket=self.file_service.bucket,
            cos_object_key=object_key,
            cos_region=self.file_service.region,
            status=DocumentStatus.UPLOADING,
            permission_tags=_normalize_tags(list(permission_tags or [])),
            created_by=created_by
        )

        await self.repo.add(document)
        task = await self.task_repo.create(document.id, IngestionTaskType.INGEST)
        await self.session.commit()
        await self.session.refresh(document)
        ingest_document_task.delay(str(document.id), str(task.id))
        return document

    # 获取文档
    async def get(
        self, document_id: UUID, *,
        permission_tags: list[str] | None = None,
    ) -> Document:
        """读取文档，并将不存在的结果转换为业务异常。"""
        doc = await self.repo.get_by_id(document_id, permission_tags=permission_tags)
        if doc is None:
            raise NotFoundError(f"文档不存在: {document_id}")
        return doc

    # 获取文档列表
    async def list_documents(
        self, page: int, page_size: int, *,
        status: DocumentStatus | None = None,
        permission_tags: list[str] | None = None,
    ) -> tuple[list[Document], int]:
        return await self.repo.list_paginated(
            page, page_size, status=status, permission_tags=permission_tags,
        )

    # 删除文档
    async def delete(self, document_id: UUID) -> None:
        doc = await self.get(document_id)
        if doc.status not in _DELETABLE_STATUSES:
            raise ValidationError(f"当前文档正在处理中，请稍后: {doc.status}")

        # 先从数据库中删除
        object_key = doc.cos_object_key
        await self.repo.delete(doc)
        await self.session.commit()
        # 再从COS存储中删除
        await self.file_service.delete(object_key)
        logger.info(f"文档删除成功: {document_id}")

    # 失败后重试操作
    async def retry(self, document_id: UUID) -> Document:
        doc = await self.get(document_id)
        if doc.status != DocumentStatus.FAILED:
            raise ValidationError(f"当前文档状态不是失败状态，无法重试: {doc.status}")
        # 防御性清理
        await self.chunk_repo.delete_by_document(document_id)
        # 更新状态并提交到数据库
        doc.status = DocumentStatus.UPLOADING
        doc.error_message = None
        task = await self.task_repo.create(doc.id, IngestionTaskType.INGEST)
        await self.session.commit()
        await self.session.refresh(doc)

        ingest_document_task.delay(str(doc.id), str(task.id))
        logger.info(f"重试文档任务执行完成: {document_id}")
        return doc

    # 获取指定文档的chunk列表
    async def list_chunks(
            self,
            document_id: UUID,
            page: int,
            page_size: int,
            *,
            permission_tags: list[str] | None = None,
    ) -> tuple[list[DocumentChunk], int, ChunkStats | None]:
        # 先确保 document 存在 + 当前用户可见
        await self.get(document_id, permission_tags=permission_tags)
        items, total = await self.chunk_repo.list_paginated_by_document(document_id, page, page_size)
        status = await self.chunk_repo.get_status(document_id)
        return items, total, status

    # 获取指定文档的Chunk内容
    async def get_chunk(
        self,
        document_id: UUID,
        chunk_id: UUID,
        *,
        permission_tags: list[str] | None = None,
    ) -> DocumentChunk:
        # 双重校验：先确保用户能看到 document，再校验 chunk 归属
        await self.get(document_id, permission_tags=permission_tags)
        chunk = await self.chunk_repo.get_for_document(document_id, chunk_id)
        if chunk is None:
            raise NotFoundError(f"文档Chunk不存在: {document_id} {chunk_id}")
        return chunk

    # admin 修改文档可见性标签
    async def update_permission_tags(
        self, document_id: UUID, tags: Sequence[str]
    ) -> Document:
        doc = await self.repo.get_by_id(document_id)
        if doc is None:
            raise NotFoundError("文档不存在")
        doc.permission_tags = _normalize_tags(tags)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc
