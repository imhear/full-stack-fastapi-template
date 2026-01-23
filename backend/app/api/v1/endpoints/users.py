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
    "/list",
    response_model=ApiResponse[List[dict]],
    summary="获取用户列表",
    description="分页获取用户列表，返回前端友好格式"
)
@permission(
    code=PermissionCode.USER_READ.value,
    name="用户查询权限",
    description="查看用户详情"
)
@inject
async def list_users(
        _superuser: CurrentSuperuser,
        user_service: UserServiceDep,
        offset: int = Query(0, ge=0, description="偏移量"),
        limit: int = Query(100, ge=1, le=500, description="每页数量")
) -> Any:
    """
    获取用户列表

    响应格式：
    {
        "code": "00000",
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
        "msg": "获取用户列表成功"
    }
    """
    try:
        users = await user_service.list_users_frontend(offset=offset, limit=limit)
        return ApiResponse.success(data=users, msg="获取用户列表成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


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
# @router.get(
#     "/",
#     response_model=UserList,
#     summary="查询用户列表",
#     description="需要【user:read】权限，仅超级用户可访问"
# )
# @permission(
#     code=PermissionCode.USER_READ.value,
#     name="用户查询权限",
#     description="查看用户列表"
# )
# @inject
# async def list_users(
#     _superuser: CurrentSuperuser,  # 无默认值（前）
#     user_service: UserServiceDep,  # 无默认值
#     _ = Depends(permission_checker(PermissionCode.USER_READ.value)),  # 有默认值（后）
#     offset: int = Query(0, ge=0),  # 查询参数（有默认值，最后）
#     limit: int = Query(100, ge=1, le=500)  # 查询参数（有默认值，最后）
# ) -> Any:
#     return await user_service.list_users(offset, limit)

from fastapi import Request
from app.api.deps import SyncSessionDep as SessionDep
from datetime import datetime
from fastapi.responses import JSONResponse
@router.get(
    "/",
    # dependencies=[Depends(get_current_active_superuser)],  # 暂时注释掉
    # response_model=UsersPublic,
)
def read_users(
        request: Request,  # 添加Request参数来获取头部信息
        current_user: CurrentUser,  # 添加当前用户验证
        pageNum: int = Query(1, description="页码", ge=1),  # 添加 pageNum 参数
        pageSize: int = Query(10, description="每页数量", ge=1, le=100),  # 添加 pageSize 参数

) -> Any:
    """
    获取用户列表 - 支持前端分页参数
    """
    # 添加详细调试信息
    print("🔵 ===== 后端用户列表接口被调用 =====")
    print(f"🔵 请求路径: {request.url}")
    print(f"🔵 请求方法: {request.method}")
    print(f"🔵 查询参数: pageNum={pageNum}, pageSize={pageSize}")

    # 检查Authorization头
    # auth_header = request.headers.get("authorization")
    # if auth_header:
    #     print(f"✅ 收到Authorization头: {auth_header[:50]}...")
    # else:
    #     print("❌ 未收到Authorization头！")
    #     print(f"🔵 所有请求头: {dict(request.headers)}")
    #
    # # 检查用户是否是超级用户
    # if not current_user.is_superuser:
    #     print(f"❌ 权限不足: 当前用户 {current_user.email} 不是超级用户")
    #     raise HTTPException(
    #         status_code=403,
    #         detail="需要管理员权限"
    #     )
    #
    # print(f"✅ 用户认证成功: {current_user.email} (ID: {current_user.id})")

    # 计算 skip
    skip = (pageNum - 1) * pageSize

    # count_statement = select(func.count()).select_from(User)
    # count = session.exec(count_statement).one()
    #
    # statement = select(User).offset(skip).limit(pageSize)
    # users = session.exec(statement).all()

    # print(f"✅ 查询成功: 总数={count}, 本次返回={len(users)}")
    print("🔵 ==================================")

    # return UsersPublic(data=users, count=count)
    # user = users[0]
    user_data = {
            "id": 123456,
            "username": "wt",
            "nickname": "wt hahah",
            "mobile": "",
            "gender": 0,
            "avatar": "",
            "email": "wt@wt.com",
            "status": 1,
            "deptName": "",
            "roleNames": "",
            "createTime": datetime.utcnow().isoformat()
        }
    list = [user_data, user_data]
    return JSONResponse({
        "code": "00000",
        "data": {
            "data":list,  # 注意这里是数组
            "page": {        #// 必须有 page 对象
              "total": 10,
              "pageNum": 1,
              "pageSize": 10
            }
        },
        "msg": "操作成功"
    })

# # 5. 分页查询用户列表（参数顺序修正）
# @router.get(
#     "/",
#     response_model=UserList,
#     summary="查询用户列表",
#     description="需要【user:read】权限，仅超级用户可访问"
# )
# @permission(
#     code=PermissionCode.USER_READ.value,
#     name="用户查询权限",
#     description="查看用户列表"
# )
# @inject
# async def list_users(
#     _superuser: CurrentSuperuser,  # 无默认值（前）
#     user_service: UserServiceDep,  # 无默认值
#     _ = Depends(permission_checker(PermissionCode.USER_READ.value)),  # 有默认值（后）
#     offset: int = Query(0, ge=0),  # 查询参数（有默认值，最后）
#     limit: int = Query(100, ge=1, le=500)  # 查询参数（有默认值，最后）
# ) -> Any:
#     return await user_service.list_users(offset, limit)

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