import json
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Query, Response, UploadFile, Form, Header

from app.db.deps import DbSession
from app.api.deps import CurrentUser, CurrentAdmin, get_current_user, RateLimited
from app.api.schemas.documents import (
    DocumentChunkDetail,
    DocumentChunkListResponse,
    DocumentChunkRead,
    DocumentChunkStats,
    DocumentListResponse,
    DocumentRead,
    DocumentStatusValue, DocumentPermissionTagsUpdate,
)
from app.db.models import DocumentStatus
from app.services.document_service import DocumentService
from app.services.permission_service import (
compute_user_permission_tags, is_admin
)

# 普通用户用于权限校验的标签，看相关文档是否可以访问
def _viewer_tags(user) -> list[str] | None:
    """ 管理视角传空，普通用户传合并后的有效标签 """
    return None if is_admin(user) else compute_user_permission_tags(user)


router = APIRouter(prefix="/documents", tags=["documents"])

""" 文档操作API """
# """上传文档到COS存储并落库"""
@router.post("", response_model=DocumentRead, status_code=201, operation_id="uploadDocument")
async def upload_document(
        admin: CurrentAdmin,
        session: DbSession,
        _rate_limit: RateLimited,
        file: UploadFile = File(..., description="待上传文档（PDF/DOCX/Markdown/HTML）"),
        permission_tags: str | None = Form(
            default=None, description="JSON 数组字符串"
        )
) -> DocumentRead:
    tags: list[str] = []
    if permission_tags:
        try:
            parsed = json.loads(permission_tags)
        except json.JSONDecodeError:
            parsed = [permission_tags]
        if isinstance(parsed, list):
            tags = [str(t) for t in parsed]
    service = DocumentService(session)
    document = await service.upload(file, created_by=admin.id, permission_tags=tags)
    return DocumentRead.model_validate(document)

# """ 根据条件分页获取文档列表 """
@router.get("", response_model=DocumentListResponse, operation_id="listDocuments")
async def list_documents(
        user: CurrentUser,
        session: DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        status: DocumentStatusValue | None = Query(None, description="按文档状态筛选")
) -> DocumentListResponse:
    service = DocumentService(session)
    items, total = await service.list_documents(
        page, page_size, status=DocumentStatus(status) if status else None,
        permission_tags=_viewer_tags(user)
    )
    return DocumentListResponse(
        items=[DocumentRead.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size
    )

# """ 根据文档ID获取单个文档 """
@router.get("/{document_id}", response_model=DocumentRead, operation_id="getDocument")
async def get_document(document_id: UUID, session: DbSession, user: CurrentUser) -> DocumentRead:
    service = DocumentService(session)
    document = await service.get(document_id, permission_tags=_viewer_tags(user))
    return DocumentRead.model_validate(document)

# """ 删除指定ID的文档 """
@router.delete("/{document_id}", status_code=204, operation_id="deleteDocument")
async def delete_document(_: CurrentAdmin, document_id: UUID, session: DbSession) -> Response:
    service = DocumentService(session)
    await service.delete(document_id)
    return Response(status_code=204)

# """ 失败后的重置操作 """
@router.post("/{document_id}/retry", response_model=DocumentRead, operation_id="retryDocument")
async def retry_document(
        _: CurrentAdmin,
        document_id: UUID,
        session: DbSession,
) -> DocumentRead:
    service = DocumentService(session)
    document = await service.retry(document_id)
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
        token: str | None = Query(None, description="Bearer token(iframe/新窗口无法带header时应用"),
        authorization: str | None = Header(None, alias="Authorization")
) -> Response:
    """ 返回文档原始字节
        支持两种认证方式，优先Header:
        1 Bearer token
        2 Basic Auth
     """
    effective_auth = authorization or (f"Bearer {token}" if token else None)
    user = await get_current_user(session, effective_auth)

    service = DocumentService(session)
    document = await service.get(document_id, permission_tags=_viewer_tags(user))
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
        user: CurrentUser,
        document_id: UUID,
        session: DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
) -> DocumentChunkListResponse:
    service = DocumentService(session)
    items, total, stats = await service.list_chunks(document_id, page, page_size, permission_tags=_viewer_tags(user))
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
        user: CurrentUser,
        document_id: UUID,
        session: DbSession,
        chunk_id: UUID,
) -> DocumentChunkDetail:
    service = DocumentService(session)
    chunk = await service.get_chunk(document_id, chunk_id, permission_tags=_viewer_tags(user))
    return DocumentChunkDetail.from_orm_chunk(chunk)


@router.patch(
    "/{document_id}/permission-tags",
    response_model=DocumentRead,
    operation_id="updateDocumentPermissionTags"
)
async def update_permission_tags(
        _: CurrentAdmin,
        document_id: UUID,
        session: DbSession,
        payload: DocumentPermissionTagsUpdate,
) -> DocumentRead:
    """  """
    service = DocumentService(session)
    document = await service.update_permission_tags(document_id, payload.permission_tags)
    return DocumentRead.model_validate(document)