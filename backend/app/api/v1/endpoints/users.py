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
import asyncio
import time
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
from app.api.deps import CurrentSuperuser, CurrentUser, UserServiceDep, DeptServiceDep

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
            "id": "用户ID",
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
        if "id" in str(e):
            error_msg += " (缺少 id 字段)"
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
    "/{user_id}/form",
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
async def get_user_form(
        user_id: str = Path(..., description="用户ID"),
        # _superuser: CurrentSuperuser = None,
        user_service: UserServiceDep = None
) -> Any:
    """
    获取指定用户信息
    """
    try:
        user_info = await user_service.get_user_form_data(user_id)
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
        _=Depends(permission_checker(PermissionCode.USER_CREATE.value)) # TODO 临时注销
) -> Any:
    """
    创建用户

    请求体：前端格式的用户数据
    响应体：前端格式的创建后用户数据
    """
    try:
        user_info = await user_service.create(user_in)
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
        print(f"🎯 API端点: 开始更新用户 {user_id}")
        print(f"📨 请求数据: {user_update.model_dump(exclude_unset=True)}")

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
# 分页查询用户列表（参数顺序修正）- 重构版
@router.get(
    "/",
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
async def read_users(
        user_service: UserServiceDep,
        dept_service: DeptServiceDep,
        # 分页参数
        pageNum: int = Query(1, description="页码", ge=1),
        pageSize: int = Query(10, description="每页数量", ge=1, le=100),
        # 排序参数 - 新增
        field: Optional[str] = Query(None, description="排序字段"),
        direction: Optional[str] = Query("DESC", description="排序方向（ASC-正序；DESC-反序）"),
        # 过滤参数 - 支持多种查询方式
        status: Optional[int] = Query(None, description="用户状态（精确匹配）"),
        status__in: Optional[str] = Query(None, description="用户状态（多选），格式：1,0"),
        username: Optional[str] = Query(None, description="用户名（精确匹配）"),
        username__like: Optional[str] = Query(None, description="用户名（模糊匹配）"),
        nickname__like: Optional[str] = Query(None, description="昵称（模糊匹配）"),
        keywords: Optional[str] = Query(None, description="综合搜索（用户名/昵称/邮箱/手机号）"),
        gender__eq: Optional[int] = Query(None, description="性别（精确匹配）"),
        gender__range: Optional[str] = Query(None, description="性别范围，格式：1-2"),
        create_time_start: Optional[date] = Query(None, alias="createTime[0]", description="创建时间起始（格式：YYYY-MM-DD）"),
        create_time_end: Optional[date] = Query(None, alias="createTime[1]", description="创建时间结束（格式：YYYY-MM-DD）"),
        mobile__like: Optional[str] = Query(None, description="手机号模糊搜索"),
        email__like: Optional[str] = Query(None, description="邮箱模糊搜索"),
        deptId: Optional[str] = Query(None, description="部门ID，筛选该部门及其所有子部门的用户")
) -> Any:
    """
    获取用户列表 - 重构版（支持策略模式查询构建器）

    支持多种查询模式：
    1. 精确查询：status=1, username="admin"
    2. 模糊查询：username__like="admi", nickname__like="管理"
    3. 多字段搜索：keywords="admin"
    4. 范围查询：gender__range="1-2", create_time_start/end
    5. IN查询：status__in="1,0"

    排序参数：
    - field: 排序字段（如：createTime, username, nickname等）
    - direction: 排序方向（ASC: 升序, DESC: 降序）

    默认排序：按创建时间降序（createTime DESC）
    """
    try:
        print("🔵 ===== 后端用户列表接口被调用（重构版）=====")

        # ========== 1. 参数处理阶段（串行，计算量小） ==========
        # 计算分页偏移量
        offset = (pageNum - 1) * pageSize

        # 构建过滤字典（使用查询构建器支持的格式）
        filters = {}

        # 如果存在deptId，获取部门ID列表
        if deptId:
            try:
                # 获取该部门及其所有子部门的ID
                dept_ids = await dept_service.get_dept_and_sub_dept_ids(deptId)
                if dept_ids:
                    # 使用IN查询筛选部门
                    filters["dept_id__in"] = dept_ids
                    print(f"🔍 部门筛选条件: dept_id__in={dept_ids}")
            except Exception as e:
                print(f"⚠️ 获取部门ID列表失败: {str(e)}")
                # 降级处理：只筛选当前部门
                filters["dept_id__eq"] = deptId

        # 处理排序参数
        if field:
            # 将前端字段名转换为数据库字段名
            field_mapping = {
                "createTime": "create_time",
                "updateTime": "update_time",
                "username": "username",
                "nickname": "nickname",
                "gender": "gender",
                "status": "status",
                "mobile": "mobile",
                "email": "email"
            }

            db_field = field_mapping.get(field, field)
            filters["sort_field"] = db_field
            filters["sort_direction"] = direction.upper() if direction else "DESC"
        else:
            # 默认排序：按创建时间降序
            filters["sort_field"] = "create_time"
            filters["sort_direction"] = "DESC"

        # 精确查询（转换为查询构建器格式）
        if status is not None:
            filters["status__eq"] = status

        if username is not None:
            filters["username__eq"] = username

        # 模糊查询
        if username__like is not None:
            filters["username__like"] = username__like

        if nickname__like is not None:
            filters["nickname__like"] = nickname__like

        if mobile__like is not None:
            filters["mobile__like"] = mobile__like

        if email__like is not None:
            filters["email__like"] = email__like

        # 多字段关键词搜索（优先使用keywords，如果同时传了keywords和具体字段，以keywords为准）
        if keywords and keywords.strip():
            filters["keywords"] = keywords.strip()

        # 范围查询
        if gender__eq is not None:
            filters["gender__eq"] = gender__eq

        if gender__range:
            try:
                min_val, max_val = map(int, gender__range.split("-"))
                filters["gender__range"] = {"min": min_val, "max": max_val}
            except ValueError:
                pass

        # 创建时间范围（兼容旧参数名和查询构建器格式）
        time_range = {}
        if create_time_start:
            time_range["start"] = create_time_start
        if create_time_end:
            time_range["end"] = create_time_end

        if time_range:
            filters["create_time_range"] = time_range

        # IN查询
        if status__in:
            try:
                status_list = [int(s.strip()) for s in status__in.split(",")]
                filters["status__in"] = status_list
            except ValueError:
                pass

        # 记录开始时间（用于性能分析）
        import time
        start_time = time.time()

        # ========== 2. 并行数据获取阶段 ==========
        # 创建并行任务
        user_future = user_service.list_users_frontend(
            offset=offset,
            limit=pageSize,
            filters=filters
        )

        dept_future = dept_service.get_dept_options_map()


        # 并行执行（关键优化点）
        user_result, dept_map = await asyncio.gather(
            user_future,
            dept_future,
            return_exceptions=True  # 确保单任务失败不影响其他任务
        )

        # 记录并行执行完成时间
        parallel_time = time.time() - start_time

        # ========== 3. 异常检查和结果处理 ==========
        # 检查用户查询异常
        if isinstance(user_result, Exception):
            raise user_result

        # 检查部门映射异常
        if isinstance(dept_map, Exception):
            dept_map = {}  # 降级处理：使用空映射

        # 解包用户结果
        users, total = user_result

        # ========== 4. 数据组装阶段（串行） ==========
        # 补充部门名称
        for user in users:
            dept_id = user.get('deptId')
            if dept_id and dept_id in dept_map:
                user['deptName'] = dept_map[dept_id]
            else:
                user['deptName'] = None

        # 计算总时间
        total_time = time.time() - start_time

        options = {
            "data": users,
            "page": {
                "total": total,
                "pageNum": pageNum,
                "pageSize": pageSize
            }
        }
        return ApiResponse.success(
            data=options,
            msg="获取字典项选项成功"
        )

    except Exception as e:
        print(f"❌ 获取用户列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


# # 6. 更新用户信息（仅超级用户）
# @router.put(
#     "/{user_id}",
#     response_model=UserOut,
#     summary="更新用户信息",
#     description="需要【user:update】权限，仅超级用户可访问"
# )
# @permission(
#     code=PermissionCode.USER_UPDATE.value,
#     name="用户更新权限",
#     description="需要【user:update】权限"
# )
# @inject
# async def update_user(
#     user_id: str,  # 路径参数
#     user_update: UserUpdate,  # 请求体
#     _superuser: CurrentSuperuser,  # 无默认值
#     user_service: UserServiceDep,  # 无默认值
#     _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
# ) -> Any:
#     return await user_service.update_user(user_id, user_update)

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