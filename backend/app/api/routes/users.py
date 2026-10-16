""" 用户相关操作接口 """
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.schemas.auth import UserRead
from app.api.schemas.users import UserPage, UserCreate, UserUpdate, AssignRolesRequest
from app.api.deps import CurrentAdmin
from app.core.exceptions import ValidationError
from app.db.models import UserStatus
from app.services.user_service import UserService
from app.db.deps import DbSession

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=UserPage, operation_id="listUsers")
async def list_users(
        _: CurrentAdmin,
        session:DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100)
) -> UserPage:
    """ 展示用户列表 """
    service = UserService(session)
    items, total = await service.list_users(page, page_size)
    return UserPage(
        items=[UserRead.model_validate(u) for u in items],
        total=total, page=page, page_size=page_size
    )

@router.post("", response_model=UserRead, status_code=201, operation_id="createUser")
async def create_user(
        _: CurrentAdmin, session: DbSession, payload: UserCreate
) -> UserRead:
    """ 创建用户 """
    service = UserService(session)
    user = await service.create_user(
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
        role_ids=payload.role_ids
    )
    return UserRead.model_validate(user)

@router.patch("/{user_id}", response_model=UserRead, operation_id="updateUser")
async def update_user(
        _: CurrentAdmin, session: DbSession, user_id: UUID, payload: UserUpdate
) -> UserRead:
    """ 更新用户信息： 昵称、状态、密码 """
    status: UserStatus | None = None
    if payload.status is not None:
        try:
            status = UserStatus(payload.status)
        except ValueError as e:
            raise ValidationError("用户状态不合法") from e
    service = UserService(session)
    user = await service.update_user(
        user_id, display_name=payload.display_name, status=status, password=payload.password
    )
    return UserRead.model_validate(user)

@router.put("/{user_id}/roles", response_model=UserRead, operation_id="assignUserRoles")
async def assign_user_roles(
        _: CurrentAdmin, session: DbSession,
        user_id: UUID, payload: AssignRolesRequest
) -> UserRead:
    """ 分配用户角色 """
    service = UserService(session)
    user = await service.set_roles(user_id, payload.role_ids)
    return UserRead.model_validate(user)

@router.delete("/{user_id}", status_code=204, operation_id="deleteUser")
async def delete_user(
        admin: CurrentAdmin, session: DbSession, user_id: UUID
) -> Response:
    """ 删除用户 """
    if admin.id == user_id:
        raise ValidationError("不能删除当前登录用户")
    service = UserService(session)
    await service.delete_user(user_id)
    return Response(status_code=204)




