from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Query, Response, UploadFile

from app.db.deps import DbSession

from app.api.schemas.documents import (
    DocumentChunkDetail,
    DocumentChunkListResponse,
    DocumentChunkRead,
    DocumentChunkStats,
    DocumentListResponse,
    DocumentRead,
    DocumentStatusValue,
)
from app.db.models import DocumentStatus
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

""" 文档操作API """
# """上传文档到COS存储并落库"""
@router.post("", response_model=DocumentRead, status_code=201, operation_id="uploadDocument")
async def upload_document(
        session: DbSession,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(..., description="待上传文档（PDF/DOCX/Markdown/HTML）")
) -> DocumentRead:
    service = DocumentService(session)
    document = await service.upload(file, background_tasks)
    return DocumentRead.model_validate(document)

# """ 根据条件分页获取文档列表 """
@router.get("", response_model=DocumentListResponse, operation_id="listDocuments")
async def list_documents(
        session: DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        status: DocumentStatusValue | None = Query(None, description="按文档状态筛选")
) -> DocumentListResponse:
    service = DocumentService(session)
    items, total = await service.list_documents(page, page_size, status=DocumentStatus(status) if status else None)
    return DocumentListResponse(
        items=[DocumentRead.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size
    )

# """ 根据文档ID获取单个文档 """
@router.get("/{document_id}", response_model=DocumentRead, operation_id="getDocument")
async def get_document(document_id: UUID, session: DbSession) -> DocumentRead:
    service = DocumentService(session)
    document = await service.get(document_id)
    return DocumentRead.model_validate(document)

# """ 删除指定ID的文档 """
@router.delete("/{document_id}", status_code=204, operation_id="deleteDocument")
async def delete_document(document_id: UUID, session: DbSession) -> Response:
    service = DocumentService(session)
    await service.delete(document_id)
    return Response(status_code=204)

# """ 失败后的重置操作 """
@router.post("/{document_id}/retry", response_model=DocumentRead, operation_id="retryDocument")
async def retry_document(
        document_id: UUID,
        session: DbSession,
        background_tasks: BackgroundTasks,
) -> DocumentRead:
    service = DocumentService(session)
    document = await service.retry(document_id, background_tasks)
    return DocumentRead.model_validate(document)

""" 文件下载和预览API """
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# 返回文档原始字节
# PDF、 HTML、 Markdown可浏览器内联与DOCX无法渲染
@router.get("/{document_id}/file", operation_id="downloadDocument")
async def download_document(
        document_id: UUID,
        session: DbSession,
        download: int = Query(0, ge=0, le=1, description="1=强制下载，0=尝试内联预览"),
) -> Response:
    service = DocumentService(session)
    document = await service.get(document_id)
    content = await service.file_service.download(document.cos_object_key)

    force_attachment = download == 1 or document.mime_type == _DOCX_MIME
    disposition = "attachment" if force_attachment else "inline"
    filename_quoted = quote(document.name, safe="")

    return Response(
        content=content,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{filename_quoted}"
            )
        }
    )

""" Chunks浏览API """

# 返回文档的chunks列表
@router.get("/{document_id}/chunks", response_model=DocumentChunkListResponse, operation_id="listDocumentChunks")
async def list_document_chunks(
        document_id: UUID,
        session: DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
) -> DocumentChunkListResponse:
    service = DocumentService(session)
    items, total, stats = await service.list_chunks(document_id, page, page_size)
    return DocumentChunkListResponse(
        items=[DocumentChunkRead.from_orm_chunk(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        stats=DocumentChunkStats(
            total=stats.total,
            avg_length=stats.avg_length,
            min_length=stats.min_length,
            max_length=stats.max_length,
        )
        if stats is not None
        else None,
    )

# 返回文档的Chunk详情，未截断的
@router.get("/{document_id}/chunks/{chunk_id}", response_model=DocumentChunkDetail, operation_id="getDocumentChunk")
async def get_document_chunk(
        document_id: UUID,
        session: DbSession,
        chunk_id: UUID,
) -> DocumentChunkDetail:
    service = DocumentService(session)
    chunk = await service.get_chunk(document_id, chunk_id)
    return DocumentChunkDetail.from_orm_chunk(chunk)
