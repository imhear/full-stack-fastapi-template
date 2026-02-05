"""
角色模块接口文件
backend/app/api/v1/endpoints/roles.py
上次更新：2025/12/1
"""
from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from typing import Annotated, List, Any

from app.di.container import Container
from app.models import SysRole
from app.schemas.responses import ApiResponse
from app.services.sys_role_service import RoleService
from app.schemas.sys_role import RoleCreate, RoleUpdate, RoleOut  # 明确导入所需Schema
from app.schemas.sys_relationship import RolePermissionAssignment
from app.schemas.sys_user import Message
from app.enums.sys_permissions import PermissionCode
from app.utils.permission_decorators import permission
from app.utils.permission_checker import permission_checker
from app.api.deps import CurrentSuperuser, RoleServiceDep  # 仅超级用户可操作

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/options",
    response_model=ApiResponse,
    summary="角色下拉选项",
    description="获取角色树形下拉选项，仅返回启用状态的部门"
)
@inject
async def get_role_options(
        role_service: RoleServiceDep
        # _current_user: CurrentUser = None
) -> Any:
    """
    获取部门下拉选项

    返回格式：
    {
        "code": "00000",
        "data": [
            {
                "value": "部门ID字符串",
                "label": "部门名称",
                "tag": "部门编码",
                "children": [...]
            }
        ],
        "msg": "获取部门选项成功"
    }
    """
    try:
        print("🔵 ===== 角色下拉选项接口被调用 =====")

        # 调试1：检查传入的dept_service类型
        print(f"🔍 调试1: role_service 类型: {type(role_service)}")
        print(f"🔍 调试1: role_service 内容: {role_service}")

        # 调试2：检查是否有get_dept_options方法
        if hasattr(role_service, 'get_dept_options'):
            print("✅ 调试2: role_service 有 get_dept_options 方法")
        else:
            print("❌ 调试2: role_service 没有 get_dept_options 方法")
            print(
                f"🔍 调试2: role_service 的所有方法: {[method for method in dir(role_service) if not method.startswith('_')]}")

        # TODO 获取角色选项，待实现数据层
        options = await role_service.get_role_options()

        print(f"✅ 获取角色选项成功: 返回{len(options)}个角色")

        return ApiResponse.success(
            data=options,
            msg="获取角色选项成功"
        )

    except Exception as e:
        print(f"❌ 获取角色选项失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取角色选项失败: {str(e)}")


# # 1. 异步查询角色列表（完善CRUD）
# @router.get("/list", response_model=List[RoleOut])
# @inject
# async def list_roles(
#     _superuser: CurrentSuperuser,
#     role_service: RoleServiceDep
# ):
#     # 需在RoleService和RoleRepository中补充list方法（见下文完善）
#     return await role_service.list_roles()


# ============ 基础CRUD操作 ============
@router.get(
    "/list",
    response_model=ApiResponse,
    summary="获取用户列表",
    description="分页获取用户列表，支持多种过滤条件，返回前端友好格式"
)
@permission(
    code=PermissionCode.USER_READ.value,
    name="用户查询权限",
    description="查看用户详情"
)
@inject
async def list_roles(
    _superuser: CurrentSuperuser,
    role_service: RoleServiceDep
)-> Any:
    """
    获取角色列表
    默认排序：按创建时间降序（createTime DESC）
    """
    # 需在RoleService和RoleRepository中补充list方法（见下文完善）
    roles = await role_service.list_roles()

    # ========== 4. 数据组装阶段（串行） ==========
    # 补充部门名称
    new_roles = []
    for role in roles:
        new_roles.append({
                "id": role.id,
                "name": role.name,
                "code": role.code,
                "status": role.status,
                "sort": role.sort,
                "createTime": role.create_time,
                "updateTime": role.update_time
            })

    total = 3
    pageNum = 1
    pageSize = 10

    options = {
        "data": new_roles,
        "page": {
            "total": total,
            "pageNum": pageNum,
            "pageSize": pageSize
        }
    }
    return ApiResponse.success(
        data=options,
        msg="获取角色列表成功"
    )
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