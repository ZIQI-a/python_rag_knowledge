""" 第一次启动时，如果没有账号，默认建一个种子用户和管理员账号 """

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.models import Role, User, UserStatus
from app.db.repositories.role_repo import RoleRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import AsyncSessionLocal
from app.services.permission_service import WILDCARD_PERMISSION_TAG

logger = get_logger(__name__)

_BUILTIN_ROLES: list[dict] = [
    {
        "name": "admin",
        "description": "管理员",
        "permission_tags": [WILDCARD_PERMISSION_TAG]
    },
    {
        "name": "user",
        "description": "普通用户",
        "permission_tags": ["public"]
    },
]

async def seed_default_admin() -> None:
    """库内无管理员时，创建管理员用户角色"""
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        if await user_repo.count_all() > 0:
            return

        logger.info("创建默认的管理员用户和角色")
        role_repo = RoleRepository(session)

        roles_by_name: dict[str, Role] = {}
        for spec in _BUILTIN_ROLES:
            existing = await role_repo.get_by_name(spec["name"])
            if existing is not None:
                roles_by_name[spec["name"]] = existing
                continue
            role = Role(
                name=spec["name"],
                description=spec["description"],
                permission_tags=spec["permission_tags"]
            )
            await role_repo.add(role)
            roles_by_name[spec["name"]] = role

        admin_user = User(
            username=settings.default_admin_username,
            password_hash=hash_password(settings.default_admin_password),
            display_name=settings.default_admin_display_name,
            status=UserStatus.ACTIVE
        )
        admin_user.roles = [roles_by_name["admin"]]
        await user_repo.add(admin_user)
        await session.commit()


