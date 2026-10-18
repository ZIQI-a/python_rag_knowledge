""" 从 Bearer token 解出 user_id、查用户、判断 admin """
from typing import Annotated

from fastapi.params import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError, PermissionDeniedError
from app.core.rate_limiter import get_rate_limiter
from app.core.security import decode_access_token
from app.db.models import  User, UserStatus
from app.db.repositories.user_repo import UserRepository
from app.services.permission_service import is_admin
from app.db.session import get_session


def _parse_bearer_token(authorization: str | None) -> str:
    """ 从请求头中取出token """
    if not authorization:
        raise UnauthorizedError("请先登录")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("无效的访问凭证")
    return token

async def get_current_user(
        session: Annotated[AsyncSession, Depends(get_session)],
        authorization: Annotated[str | None, Header(alias="Authorization")] = None
) -> User:
    """ 解析token查表拿到User """
    token = _parse_bearer_token(authorization)
    subject = decode_access_token(token)
    try:
        from uuid import UUID
        user_id = UUID(subject)
    except (ValueError, TypeError) as e:
        raise UnauthorizedError("无效的访问凭证") from e

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("用户不存在")
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("用户已被封禁")
    return user

async def get_current_admin(
        user: Annotated[User, Depends(get_current_user)],
) -> User:
    """ 仅管理员可访问 """
    if not is_admin(user):
        raise PermissionDeniedError("抱歉，您无权访问")

    return user

# 挂载限流
async def enforce_rate_limiter(
        user: Annotated[User, Depends(get_current_user)]
) -> None:
    """ 滑动窗口限流，按用户每分钟限流 """
    if not settings.rate_limit_enabled:
        return
    await get_rate_limiter().check(f"user:{user.id}")

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
RateLimited = Annotated[None, Depends(enforce_rate_limiter)]
