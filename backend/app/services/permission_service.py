""" 权限相关服务 """

from app.db.models import User

# 通配权限标签，一般为管理员持有
WILDCARD_PERMISSION_TAG = "*"
# 内置角色名
ADMIN_ROLE_NAME = "admin"

def compute_user_permission_tags(user: User) -> list[str]:
    """ 合并角色权限标签，并去重 """
    merged: set[str] = set()
    for role in user.roles:
        for tag in role.permission_tags:
            if tag == WILDCARD_PERMISSION_TAG:
                return [WILDCARD_PERMISSION_TAG]
            merged.add(tag)
    return sorted(merged)

def is_admin(user: User) -> bool:
    """ 是否是管理员 """
    return any(role.name == ADMIN_ROLE_NAME for role in user.roles)
