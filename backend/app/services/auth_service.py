""" 登录校验 """
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import verify_password, create_access_token
from app.db.repositories.user_repo import UserRepository

from app.db.models import User, UserStatus

logger = get_logger(__name__)

class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate(self, username: str, password: str) -> User | None:
        """ 登录用户校验 """
        user = await self.user_repo.get_by_username(username)
        if user is None:
            return None
        if user.status != UserStatus.ACTIVE:
            logger.info("登录被拒绝: username=%s", username)
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def issue_token(user: User) -> str:
        return create_access_token(str(user.id))


