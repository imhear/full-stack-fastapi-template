"""
backend/app/api/v1/endpoints/users.py
上次更新：2026/1/21
用户API端点 - 集成统一响应格式和字段映射

设计原则：
1. 最小API逻辑：只处理HTTP相关逻辑
2. 依赖注入：通过依赖获取服务实例
3. 统一响应：所有接口返回标准格式
4. 错误处理：统一异常处理
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path
from dependency_injector.wiring import inject
from typing import Any, List, Optional
from datetime import date

# from fastapi import Request
# from app.api.deps import SyncSessionDep as SessionDep
# from datetime import datetime, date
from fastapi.responses import JSONResponse

from app.schemas.responses import ApiResponse

from app.core.exceptions import BadRequest, ResourceNotFound
from app.schemas.sys_user import (
    UserCreate, UserUpdate, Message, UserUpdateSelfPassword, UserOut, UserList, UserMeResponse
)
from app.enums.sys_permissions import PermissionCode
from app.utils.permission_decorators import permission
from app.utils.permission_checker import permission_checker
from app.api.deps import CurrentSuperuser, CurrentUser, UserServiceDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=ApiResponse[UserMeResponse],  # 使用 UserMeResponse 模型
    summary="获取当前用户信息",
    description="获取已登录用户的个人信息，返回前端友好格式"
)
@inject
async def read_me(
        current_user: CurrentUser,
        user_service: UserServiceDep
) -> Any:
    """
    获取当前用户信息

    响应格式：
    {
        "code": "00000",
        "data": {
            "userId": "用户ID",
            "username": "用户名",
            "nickname": "昵称",
            "avatar": "头像URL",
            "roles": ["角色代码"],
            "perms": ["权限代码"]
        },
        "msg": "获取用户信息成功"
    }
    """
    try:
        user_info = await user_service.get_current_user_info(current_user)

        # 使用 UserMeResponse 模型进行验证和序列化
        user_me_response = UserMeResponse(**user_info)

        return ApiResponse.success(
            data=user_me_response.model_dump(),  # Pydantic 自动处理序列化
            msg="获取用户信息成功"
        )
    except Exception as e:
        # 记录详细的错误信息
        import traceback
        print(f"获取用户信息失败: {str(e)}")
        print(traceback.format_exc())
        # 提供更有用的错误信息
        error_msg = f"获取用户信息失败: {str(e)}"
        if "userId" in str(e):
            error_msg += " (缺少 userId 字段)"
        raise HTTPException(status_code=500, detail=error_msg)


@router.get(
    "/profile",
    response_model=ApiResponse[dict],
    summary="获取个人中心信息",
    description="获取用户的个人中心详细信息"
)
@inject
async def get_profile(
        current_user: CurrentUser,
        user_service: UserServiceDep
) -> Any:
    """
    获取个人中心信息

    响应格式：
    {
        "code": "00000",
        "data": {
            "id": "用户ID",
            "username": "用户名",
            "nickname": "昵称",
            "avatar": "头像URL",
            "gender": 1,
            "mobile": "手机号",
            "email": "邮箱",
            "deptName": "部门名称",
            "roleNames": "角色名称",
            "createTime": "创建时间"
        },
        "msg": "获取个人中心信息成功"
    }
    """
    try:
        profile = await user_service.get_user_profile(current_user.id)
        return ApiResponse.success(data=profile, msg="获取个人中心信息成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取个人中心信息失败: {str(e)}")


@router.get(
    "/{user_id}/info",
    response_model=ApiResponse[dict],
    summary="获取指定用户信息",
    description="根据用户ID获取用户信息"
)
@permission(
    code=PermissionCode.USER_READ.value,
    name="用户查询权限",
    description="查看用户详情"
)
@inject
async def get_user_info(
        user_id: str = Path(..., description="用户ID"),
        _superuser: CurrentSuperuser = None,
        user_service: UserServiceDep = None
) -> Any:
    """
    获取指定用户信息
    """
    try:
        user_info = await user_service.get_user_info(user_id)
        return ApiResponse.success(data=user_info, msg="获取用户信息成功")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.post(
    "/",
    response_model=ApiResponse[dict],
    summary="创建用户",
    description="创建新用户并返回创建后的用户信息"
)
@permission(
    code=PermissionCode.USER_CREATE.value,
    name="用户创建权限",
    description="需要【user:create】权限"
)
@inject
async def create_user(
        user_in: UserCreate,
        _superuser: CurrentSuperuser,
        user_service: UserServiceDep,
        _=Depends(permission_checker(PermissionCode.USER_CREATE.value))
) -> Any:
    """
    创建用户

    请求体：前端格式的用户数据
    响应体：前端格式的创建后用户数据
    """
    try:
        user_info = await user_service.create_user(user_in)
        return ApiResponse.success(data=user_info, msg="用户创建成功")
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户创建失败: {str(e)}")


@router.put(
    "/{user_id}",
    response_model=ApiResponse[dict],
    summary="更新用户信息",
    description="更新用户信息并返回更新后的用户信息"
)
@permission(
    code=PermissionCode.USER_UPDATE.value,
    name="用户更新权限",
    description="需要【user:update】权限"
)
@inject
async def update_user(
        user_id: str,
        user_update: UserUpdate,
        _superuser: CurrentSuperuser,
        user_service: UserServiceDep,
        _=Depends(permission_checker(PermissionCode.USER_UPDATE.value))
) -> Any:
    """
    更新用户信息
    """
    try:
        user_info = await user_service.update_user(user_id, user_update)
        return ApiResponse.success(data=user_info, msg="用户信息更新成功")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户信息更新失败: {str(e)}")


# @router.delete(
#     "/{user_id}",
#     response_model=ApiResponse[dict],
#     summary="删除用户",
#     description="删除指定用户"
# )
# @permission(code=PermissionCode.USER_DELETE.value)
# @inject
# async def delete_user(
#         user_id: str,
#         _superuser: CurrentSuperuser,
#         user_service: UserServiceDep,
#         _=Depends(permission_checker(PermissionCode.USER_DELETE.value))
# ) -> Any:
#     """
#     删除用户
#     """
#     try:
#         result = await user_service.delete_user(user_id)
#         return ApiResponse.success(data={"deleted": True}, msg=result.message)
#     except ResourceNotFound as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"用户删除失败: {str(e)}")
#
# ==============

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
    "/me/old",
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
    response_model=ApiResponse,
    summary="获取用户列表",
    description="分页获取用户列表，支持状态、时间范围、关键词过滤，返回前端友好格式"
)
@permission(
    code=PermissionCode.USER_READ.value,
    name="用户查询权限",
    description="查看用户详情"
)
@inject
async def read_users(
        user_service: UserServiceDep,
        # 分页参数
        pageNum: int = Query(1, description="页码", ge=1),
        pageSize: int = Query(10, description="每页数量", ge=1, le=100),
        # 新增过滤参数
        status: Optional[int] = Query(None, description="用户状态（1=启用，0=禁用）"),
        createTime0: Optional[date] = Query(None, alias="createTime[0]", description="创建时间起始（格式：YYYY-MM-DD）"),
        createTime1: Optional[date] = Query(None, alias="createTime[1]", description="创建时间结束（格式：YYYY-MM-DD）"),
        keywords: Optional[str] = Query(None, description="搜索关键词（匹配用户名/昵称/手机号）")
) -> Any:
    """
    获取用户列表

    响应格式：
    {
        "code": "00000",
        "data": {
            "data": [
                {
                    "id": "用户ID",
                    "username": "用户名",
                    "nickname": "昵称",
                    "avatar": "头像",
                    "gender": 1,
                    "mobile": "手机号",
                    "email": "邮箱",
                    "deptName": "部门名称",
                    "roleNames": "角色名称",
                    "createTime": "创建时间",
                    "status": 1
                }
            ],
            "page": {
                "total": 100,
                "pageNum": 1,
                "pageSize": 10
            }
        },
        "msg": "获取用户列表成功"
    }
    """
    try:
        print("🔵 ===== 后端用户列表接口被调用 =====")
        print(f"📋 查询参数: pageNum={pageNum}, pageSize={pageSize}, status={status}, "
              f"createTime0={createTime0}, createTime1={createTime1}, keywords={keywords}")

        # 计算分页偏移量
        offset = (pageNum - 1) * pageSize

        # 构建过滤条件
        filters = {}
        if status is not None:
            filters["status"] = status
        if createTime0 is not None:
            filters["create_time_start"] = createTime0
        if createTime1 is not None:
            filters["create_time_end"] = createTime1
        if keywords and keywords.strip():
            filters["keywords"] = keywords.strip()

        # 调用服务层
        users, total = await user_service.list_users_frontend(
            offset=offset,
            limit=pageSize,
            filters=filters
        )

        print(f"✅ 查询成功: 返回{len(users)}条数据，总数{total}条")

        return JSONResponse({
            "code": "00000",
            "data": {
                "data": users,  # 用户列表数据
                "page": {  # 分页信息
                    "total": total,
                    "pageNum": pageNum,
                    "pageSize": pageSize
                }
            },
            "msg": "操作成功"
        })
    except Exception as e:
        print(f"❌ 获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


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
    description="需要【user:update】权限"
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


# 在 users.py 中添加一个测试端点
@router.get("/test-serialize", include_in_schema=False)
@inject
async def test_serialize(
        current_user: CurrentUser,
        user_service: UserServiceDep
) -> Any:
    """
    测试用户对象序列化
    """
    try:
        # 获取用户信息
        user_info = await user_service.get_current_user_info(current_user)

        # 尝试使用 UserMeResponse 模型
        try:
            user_me_response = UserMeResponse(**user_info)
            serialized = user_me_response.model_dump()

            # 尝试 JSON 序列化
            import json
            json.dumps(serialized)

            return {
                "success": True,
                "message": "序列化成功",
                "data": serialized
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"序列化失败: {str(e)}",
                "data": user_info
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取用户信息失败: {str(e)}"
        }