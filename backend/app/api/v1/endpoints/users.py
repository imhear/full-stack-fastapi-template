"""
用户模块接口文件
backend/app/api/v1/endpoints/users.py
上次更新：2025/12/26
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from dependency_injector.wiring import inject
from typing import Any, List

from app.schemas.sys_user import UserCreate, UserOut, UserUpdate, Message, UserList, UserUpdateSelfPassword
from app.enums.sys_permissions import PermissionCode
from app.utils.permission_decorators import permission
from app.utils.permission_checker import permission_checker
from app.api.deps import CurrentSuperuser, CurrentUser, UserServiceDep

router = APIRouter(prefix="/users", tags=["users"])


# 1. 创建用户（仅超级用户）
@router.post(
    "/",
    response_model=UserOut,
    summary="创建新用户",
    description="需要【user:create】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_CREATE.value,
    name="用户创建权限",
    description="创建新用户的核心权限"
)
@inject
async def create_user(
    *,
    user_in: UserCreate,  # 无默认值（请求体）
    _superuser: CurrentSuperuser,  # 无默认值（超级用户依赖）
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_CREATE.value))  # 有默认值
) -> Any:
    return await user_service.create_user(user_in)

# 2. 创建用户+分配角色（扩展接口）
@router.post(
    "/with-roles",
    response_model=UserOut,
    summary="创建用户并分配角色",
    description="需要【user:create】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_CREATE.value,
    name="用户创建权限",
    description="创建用户并分配角色"
)
@inject
async def create_user_with_roles(
    *,
    user_in: UserCreate,  # 请求体
    role_ids: List[str],  # 请求体（需确保Pydantic模型支持）
    _superuser: CurrentSuperuser,
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_CREATE.value))
) -> Any:
    return await user_service.create_user_with_roles(user_in, role_ids)

# 3. 获取当前用户信息
@router.get(
    "/me",
    response_model=UserOut,
    summary="获取个人信息",
    description="已登录用户可访问"
)
async def read_me(
    current_user: CurrentUser  # 无默认值
) -> Any:
    return current_user

# 4. 获取用户详情（仅超级用户）
@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="查询用户详情",
    description="需要【user:read】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_READ.value,
    name="用户查询权限",
    description="查看用户详情"
)
@inject
async def get_user(
    user_id: str,  # 路径参数（无默认值）
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_READ.value))  # 有默认值
) -> Any:
    return await user_service.get_user_by_id(user_id)

# 5. 分页查询用户列表（参数顺序修正）
@router.get(
    "/",
    response_model=UserList,
    summary="查询用户列表",
    description="需要【user:read】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_READ.value,
    name="用户查询权限",
    description="查看用户列表"
)
@inject
async def list_users(
    _superuser: CurrentSuperuser,  # 无默认值（前）
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_READ.value)),  # 有默认值（后）
    offset: int = Query(0, ge=0),  # 查询参数（有默认值，最后）
    limit: int = Query(100, ge=1, le=500)  # 查询参数（有默认值，最后）
) -> Any:
    return await user_service.list_users(offset, limit)

# 6. 更新用户信息（仅超级用户）
@router.put(
    "/{user_id}",
    response_model=UserOut,
    summary="更新用户信息",
    description="需要【user:update】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_UPDATE.value,
    name="用户更新权限",
    description="修改用户信息"
)
@inject
async def update_user(
    user_id: str,  # 路径参数
    user_update: UserUpdate,  # 请求体
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
) -> Any:
    return await user_service.update_user(user_id, user_update)

# 7. 删除用户（仅超级用户）
@router.delete(
    "/{user_id}",
    response_model=Message,
    summary="删除用户",
    description="需要【user:delete】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_DELETE.value,
    name="用户删除权限",
    description="删除用户"
)
@inject
async def delete_user(
    user_id: str,  # 路径参数
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_DELETE.value))  # 有默认值
) -> Any:
    return await user_service.delete_user(user_id)

# 8. 为用户分配角色（仅超级用户）
@router.post(
    "/{user_id}/roles",
    response_model=Message,
    summary="分配用户角色",
    description="需要【user:update】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_UPDATE.value,
    name="用户更新权限",
    description="修改用户角色"
)
@inject
async def assign_user_roles(
    user_id: str,  # 路径参数
    role_ids: List[str],  # 请求体
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
) -> Any:
    return await user_service.assign_roles(user_id, role_ids)

# 9. 更新用户密码（仅超级用户）
@router.post(
    "/{user_id}/password",
    response_model=Message,
    summary="重置用户密码",
    description="需要【user:update】权限，仅超级用户可访问"
)
@permission(
    code=PermissionCode.USER_UPDATE.value,
    name="用户更新权限",
    description="重置用户密码"
)
@inject
async def reset_user_password(
    user_id: str,  # 路径参数
    new_password: str,  # 请求体
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
) -> Any:
    return await user_service.update_password(user_id, new_password)

# 10. 更新个人信息（当前用户）
@router.put(
    "/me",
    response_model=UserOut,
    summary="更新个人信息",
    description="已登录用户可访问"
)
@inject
async def update_me(
    user_update: UserUpdate,  # 请求体
    current_user: CurrentUser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
) -> Any:
    return await user_service.update_user(current_user.id, user_update)

# 11. 修改个人密码（当前用户）
@router.put(
    "/me/password",
    response_model=Message,
    summary="修改个人密码",
    description="已登录用户修改自己的密码，幂等操作"
)
@inject
async def update_me_password(
    user_update: UserUpdateSelfPassword,  # 请求体
    current_user: CurrentUser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
) -> Any:
    return await user_service.update_self_password(current_user.id, user_update)
