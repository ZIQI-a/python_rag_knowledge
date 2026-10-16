""" 安全相关工具函数 """
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

def has_password(plain: str) -> str:
    """ bcrypt默认cost等于12，单次哈希200毫秒 """
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False

""" JWT用户权限签发与解码 """
def create_access_token(subject: str) -> str:
    """ JWT, 约定放User ID字符串 """
    if not settings.jwt_secret:
        raise UnauthorizedError("服务端配置JWT密钥无法签发Token")
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp())
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> str:
    """ 返回token中sub字段 """
    if not settings.jwt_secret:
        raise UnauthorizedError("服务端未配置JWT secret")
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as e:
        raise UnauthorizedError("许久未来了,需验明身份") from e
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError("访问无效凭证") from e

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise UnauthorizedError("无效的访问凭证")
    return subject

