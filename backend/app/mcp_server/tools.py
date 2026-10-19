import base64

import binascii
from typing import Literal

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.mcp_server.auth import resolve_current_user, require_admin
from app.mcp_server.schemas import MCPAskAnswer, MCPCitation, MCPUploadResult, MCPDocumentList, MCPDocumentItem
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.permission_service import is_admin, compute_user_permission_tags
from app.api.schemas.documents import DocumentStatusValue
from app.db.models import DocumentStatus


logger = get_logger(__name__)

def register_tools(mcp: FastMCP) -> None:
    """ 5个知识库工具挂到给定的Fast MCP实例 """
    @mcp.tool(
        name="ask_knowledge_base",
        title="知识库问答",
        description=(
                "向知识库提问并得到带引用的答案。检索按调用者的权限标签过滤；"
                "命中阈值不足或答案校验未通过时返回 refused=true 与统一拒答文案。"
        )
    )
    async def ask_knowledge_base(question: str, ctx: Context) -> MCPAskAnswer:
        """ 知识库问答 """
        user = await resolve_current_user(ctx)
        question = question.strip()
        if not question:
            raise ToolError("Question不能为空")
        # 调用问答服务
        async with AsyncSessionLocal() as session:
            service = ChatService(session)
            try:
                result = await service.answer_for_mcp(question, current_user=user)
            except Exception as exc:
                raise _to_tool_error(exc, default="问答处理失败") from exc

        citations = [
            MCPCitation(
                ordinal=int(c["ordinal"]),
                document_id=c["document_id"],
                document_name=c["document_name"],
                page_no=c["page_no"],
                section_path=c.get("section_path"),
                quote=c.get("quote", "")
            )
            for c in result.citations
        ]
        return MCPAskAnswer(
            answer=result.answer,
            refused=result.refused,
            citations=citations,
            trace_id=result.trace_id
        )

    @mcp.tool(
        name="upload_document",
        title="上传文档",
        description=(
                "上传文件到知识库（仅管理员）。content_base64 是文件原字节的 "
                "base64 编码；服务端按 sha256 做幂等，相同内容会复用现有文档。"
                "解析与向量化由 Celery 异步执行，调用方可通过 get_document_status 轮询进度。"
        ),
    )
    async def upload_document(
            filename: str, content_base64: str, ctx: Context,
            mime_type: str | None = None, permission_tags: list[str] | None = None
    ) -> MCPUploadResult:
        """ MCP文档上传 """
        admin = await resolve_current_user(ctx)
        require_admin(admin)

        if not filename.strip():
            raise ToolError("文件名不能为空")

        try:
            content = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ToolError("内容 base64 解码失败,不是合法的Base64编码") from exc

        upload_file = _Base64UploadFile(
            filename=filename,
            content=content,
            content_type=mime_type
        )

        async with AsyncSessionLocal() as session:
            service = DocumentService(session)
            try:
                document = await service.upload(
                    upload_file, created_by=admin.id, permission_tags=permission_tags
                )
            except Exception as exc:
                raise _to_tool_error(exc, default="文档上传失败") from exc

        return MCPUploadResult(
            document_id=document.id,
            name=document.name,
            status=_status_value(document.status),
            version=document.version,
            file_hash=document.file_hash,
        )

    @mcp.tool(
        name="list_documents",
        title="列出文档",
        description="按更新时间倒序分页列出当前用户可见的文档"
    )
    async def list_documents(
            ctx: Context, page: int = 1, page_size: int = 20,
            status: DocumentStatusValue | None = None
    ) -> MCPDocumentList:
        user = await resolve_current_user(ctx)
        if page < 1:
            raise ToolError("页码必须大于等于1")
        if page_size < 1 or page_size > 100:
            raise ToolError("页大小必须在1-100之间")

        async with AsyncSessionLocal() as session:
            service = DocumentService(session)
            try:
                items, total = await service.list_documents(
                    page, page_size, status=DocumentStatus(status) if status else None,
                    permission_tags=_viewer_tags(user)
                )
            except Exception as exc:
                raise _to_tool_error(exc, default="文档列表获取失败") from exc

        return MCPDocumentList(
            items=[MCPDocumentItem.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size
        )



def _to_tool_error(exc: Exception, *, default: str) -> ToolError:
    """ 统一把异常翻译为MCP tool error """
    if isinstance(exc, AppException):
        return ToolError(exc.message)
    logger.exception("MCP tool unexpected error")
    return ToolError(default)

class _Base64UploadFile:
    """ 把Bytes包装成兼容FastAPI的Upload的轻量对象 """
    def __init__(self, *, filename: str, content: bytes, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type or ""
        self._content = content

    async def read(self) -> bytes:
        return self._content

# 权限标签查询(指定用户的)
def _viewer_tags(user) -> list[str] | None:
    """ 查询指定用户的权限标签 """
    return None if is_admin(user) else compute_user_permission_tags(user)

def _status_value(status: DocumentStatus) -> DocumentStatusValue:
    """枚举 → 字面量字符串，让 MCP schema 字段稳定为联合字面量。"""
    return status.value  # type: ignore[return-value]

def _task_type_value(task) -> Literal["ingest", "reindex"] | None:
    """ 获取任务的类型是首次创建还是增量 """
    return task.task_type.value if task else None

def _task_status_value(task):
    """ 获取任务的状态 """
    return task.status.value if task else None

def _parse_uuid(raw: str, *, field: str):
    """ 检查给定的字符串是否为合法的 UUID """
    from uuid import UUID

    try:
        return UUID(raw)
    except (TypeError, ValueError) as exc:
        raise ToolError(f"{field} 不是合法的 UUID") from exc

