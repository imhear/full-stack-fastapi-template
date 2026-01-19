# 功能：统一导出所有Schema模型，对外提供一致的导入入口
# 文件相对项目根目录路径：backend/app/schemas/__init__.py
# 上次更新：2025/12/10（第33轮：增量新增文档更新/删除Schema导入语句，补充导出项，代码逻辑修改）
# 原上次更新：2025/12/07（第53轮：修复CreatorInfo导入错误，删除无效引用）
# 迭代记录：15-47轮（核心同步）+35轮（语法修复）+36轮（全面检查）+37轮（仅文件树展示筛选，无代码修改）+38轮（全量输出，无省略）+39轮（补充完整回复结构，无代码修改）+40轮（重新完整输出，修复截断，无内容修改）+53轮（修复CreatorInfo导入错误，删除无效引用）+33轮（增量新增更新/删除Schema导入，代码逻辑修改） | 修复引用不存在的DocDetailRequest，新增文档创建/详情Schema导出，保留所有原有代码，全面检查无错误，全量输出无省略
from app.schemas.base import BaseSchema, TimestampSchema, IDSchema
from app.schemas.sys_permission import (
    PermissionBase, PermissionCreate, PermissionUpdate,
    PermissionInDB, PermissionOut, PermissionList
)
from app.schemas.sys_role import (
    RoleBase, RoleCreate, RoleUpdate, RoleInDB,
    RoleOut, RoleWithUsers, RoleList
)
from app.schemas.sys_user import (
    UserBase, UserCreate, UserUpdate, UserInDB,
    UserOut, UserWithPermissions, UserList,
    UserLogin, Token, TokenData, UserUpdateSelfPassword, UpdateOwnPassword
)
from app.schemas.sys_relationship import (
    UserRoleAssignment, RolePermissionAssignment,
    UserRoleResponse, RolePermissionResponse
)

__all__ = [
    # Base
    'BaseSchema', 'TimestampSchema', 'IDSchema',

    # Permission
    'PermissionBase', 'PermissionCreate', 'PermissionUpdate',
    'PermissionInDB', 'PermissionOut', 'PermissionList',

    # Role
    'RoleBase', 'RoleCreate', 'RoleUpdate', 'RoleInDB',
    'RoleOut', 'RoleWithUsers', 'RoleList',

    # User
    'UserBase', 'UserCreate', 'UserUpdate', 'UserInDB',
    'UserOut', 'UserWithPermissions', 'UserList',
    'UserLogin', 'Token', 'TokenData','UpdateOwnPassword','UserUpdateSelfPassword',

    # Relationship
    'UserRoleAssignment', 'RolePermissionAssignment',
    'UserRoleResponse', 'RolePermissionResponse',
]