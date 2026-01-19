"""
模型统一导出文件，解决循环依赖问题，按依赖顺序导入并导出所有模型及中间表
backend/app/models/__init__.py
上次更新：2026/1/19
"""
# 首先导入Base
from app.models.base import Base

# 然后导入各个模型（严格按依赖顺序：先无依赖，后有依赖）
from app.models.sys_permission import SysPermission
from app.models.sys_role import SysRole, sys_role_permissions
from app.models.sys_user import SysUser, sys_user_roles

# 导出所有模型+中间表（按导入顺序排列，便于维护）
__all__ = [
    'Base',
    'SysUser',
    'SysRole',
    'SysPermission',
    'sys_user_roles',
    'sys_role_permissions',
]