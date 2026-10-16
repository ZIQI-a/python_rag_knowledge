""" 角色相关操作 """
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.role_repo import RoleRepository
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.db.models import Role

PROTECTED_ROLE_NAMES = frozenset({"admin", "user"})

class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RoleRepository(session)

    async def list_role(self) -> list[Role]:
        """ 展示所有角色列表 """
        return await self.repo.list_all()

    async def get_role(self, role_id: UUID) -> Role:
        """ 根据角色ID获取角色 """
        role = await self.repo.get_by_id(role_id)
        if role is None:
            raise NotFoundError("角色不存在")
        return role

    async def create_role(
            self, * , name: str, description: str, permission_tags: list[str]
    ) -> Role:
        """ 创建新角色 """
        name = name.strip()
        if not name:
            raise ValidationError("角色名不能为空")
        if await self.repo.get_by_name(name) is not None:
            raise ConflictError(f"角色 {name} 已存在")
        role = Role(
            name=name, description=description.strip(), permission_tags=_normalize_tags(permission_tags)
        )
        await self.repo.add(role)
        await self.session.commit()
        return role

    async def update_role(
            self, role_id: UUID, *,
            description: str | None = None,
            permission_tags: list[str] | None = None
    ) -> Role:
        """ 更新指定ID的角色 """
        role = await self.get_role(role_id)
        if description is not None:
            role.description = description.strip()
        if permission_tags is not None:
            role.permission_tags = _normalize_tags(permission_tags)
        await self.session.commit()
        return role

    async def delete_role(self, role_id: UUID) -> None:
        role = await self.get_role(role_id)
        if role.name in PROTECTED_ROLE_NAMES:
            raise ValidationError(f"内置角色{role.name}不允许删除")
        await self.repo.delete(role)
        await self.session.commit()


def _normalize_tags(tags: list[str]) -> list[str]:
    """去空白、去空串、去重、保持稳定顺序。"""
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        t = tag.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result
