"""
角色模块接口文件
backend/app/api/v1/endpoints/roles.py
上次更新：2025/12/1
"""
from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from typing import Annotated, List

from app.di.container import Container
from app.services.sys_role_service import RoleService
from app.schemas.sys_role import RoleCreate, RoleUpdate, RoleOut  # 明确导入所需Schema
from app.schemas.sys_relationship import RolePermissionAssignment
from app.schemas.sys_user import Message
from app.enums.sys_permissions import PermissionCode
from app.utils.permission_decorators import permission
from app.utils.permission_checker import permission_checker
from app.api.deps import CurrentSuperuser, RoleServiceDep  # 仅超级用户可操作

router = APIRouter(prefix="/roles", tags=["roles"])


# 1. 异步查询角色列表（完善CRUD）
@router.get("/", response_model=List[RoleOut])
@inject
async def list_roles(
    _superuser: CurrentSuperuser,
    role_service: RoleServiceDep
):
    # 需在RoleService和RoleRepository中补充list方法（见下文完善）
    return await role_service.list_roles()

# 2. 异步查询角色详情
@router.get("/{role_id}", response_model=RoleOut)
@inject
async def get_role(
    role_id: str,
    _superuser: CurrentSuperuser,
    role_service: RoleService = Depends(Provide[Container.role_service])
):
    return await role_service.get_role_by_id(role_id)

# 3. 异步创建角色
@router.post(
"/",
    response_model=RoleOut,
    description="""
    创建新角色（仅超级管理员可操作）：
    - 若permissions表为空，请勿传入permission_ids（会返回400错误）
    - 角色编码（code）必须唯一
    - is_active默认为true
    """
)
@permission(code=PermissionCode.ROLE_MANAGE.value, name="角色创建权限")
@inject  # 保持最后一个装饰器
async def create_role(
    role_in: RoleCreate,
    _superuser: CurrentSuperuser,  # 无额外Depends（已内置）
    role_service: RoleService = Depends(Provide[Container.role_service]),
    _ = Depends(permission_checker(PermissionCode.ROLE_MANAGE.value))
):
    return await role_service.create_role(role_in)

# 4. 异步为角色分配权限
@router.post("/{role_id}/permissions", response_model=Message)
@permission(code=PermissionCode.ROLE_MANAGE.value, name="角色分配权限")
@inject
async def assign_permissions(
    role_id: str,
    assignment: RolePermissionAssignment,
    _superuser: CurrentSuperuser,
    role_service: RoleService = Depends(Provide[Container.role_service]),
    _ = Depends(permission_checker(PermissionCode.ROLE_MANAGE.value))
):
    return await role_service.assign_permissions(role_id, assignment.permission_ids)

# 5. 异步更新角色
@router.put("/{role_id}", response_model=RoleOut)
@permission(code=PermissionCode.ROLE_MANAGE.value, name="角色更新权限")
@inject
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    _superuser: CurrentSuperuser,
    role_service: RoleService = Depends(Provide[Container.role_service]),
    _ = Depends(permission_checker(PermissionCode.ROLE_MANAGE.value))
):
    return await role_service.update_role(role_id, role_update)

# 6. 异步删除角色
@router.delete("/{role_id}", response_model=Message)
@permission(code=PermissionCode.ROLE_MANAGE.value, name="角色删除权限")
@inject
async def delete_role(
    role_id: str,
    _superuser: CurrentSuperuser,
    role_service: RoleService = Depends(Provide[Container.role_service]),
    _ = Depends(permission_checker(PermissionCode.ROLE_MANAGE.value))
):
    return await role_service.delete_role(role_id)