""" HTTP 请求头里的 JWT”转换成“MCP 工具能用的 User 对象”"""
from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError

from app.core.exceptions import UnauthorizedError, AppException
from app.core.security import decode_access_token
from app.db.models import User, UserStatus
from app.db.repositories.user_repo import UserRepository
from app.db.session import AsyncSessionLocal
from app.services.permission_service import is_admin


def _parse_bearer_token(authorization: str | None) -> str:
    """ 从请求头中取出token """
    if not authorization:
        raise UnauthorizedError("请先登录")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("无效的访问凭证")
    return token

async def resolve_current_user(ctx: Context) -> User:
    """ 从MPCP context取出token并查到活跃用户 """
    request = getattr(ctx.request_context, "request", None)
    if request is None:
        # stdio等无http上下文传输模式不支持
        raise ToolError("当前传输不支持鉴权")

    try:
        token = _parse_bearer_token(request.headers.get("Authorization"))
        subject = decode_access_token(token)
        user_id = UUID(subject)
    except (AppException, ValueError) as e:
        raise ToolError(_user_facing_message(e, default="无效的访问凭证")) from e

    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(user_id)

    if user is None:
        raise ToolError("用户不存在或已删除")
    if user.status != UserStatus.ACTIVE:
        raise ToolError("用户已被封禁")
    return user

def require_admin(user: User) -> None:
    """ admin-only 工具入口处调用 """
    if not is_admin(user):
        raise ToolError("无权限访问")

def _user_facing_message(exc: Exception, *, default: str) -> str:
    """ 统一把异常信息透出给Agent """
    if isinstance(exc, AppException):
        return exc.message
    return default
