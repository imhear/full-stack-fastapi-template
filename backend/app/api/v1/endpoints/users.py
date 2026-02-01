"""
backend/app/api/v1/endpoints/users.py
更新时间：2026/1/31
用户API端点 - RPC风格URL重构

设计原则：
1. RPC风格URL设计，路径明确表达操作意图
2. 最小API逻辑：只处理HTTP相关逻辑
3. 依赖注入：通过依赖获取服务实例
4. 统一响应：所有接口返回标准格式
5. 错误处理：统一异常处理
"""
import asyncio
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path
from dependency_injector.wiring import inject
from typing import Any, List, Optional
from datetime import date

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


# ============ 个人相关接口 ============
@router.get(
    "/get-me",
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
    "/get-profile",
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


@router.put(
    "/update-me",
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


@router.put(
    "/update-me-password",
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


@router.get(
    "/get/{id}",
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
        id: str = Path(..., description="用户ID"),
        # _superuser: CurrentSuperuser = None,
        user_service: UserServiceDep = None
) -> Any:
    """
    获取指定用户信息
    """
    try:
        user_info = await user_service.get_user_form_data(id)
        return ApiResponse.success(data=user_info, msg="获取用户信息成功")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.post(
    "/create",
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


@router.post(
    "/update/{id}",
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
        id: str,
        user_update: UserUpdate,
        _superuser: CurrentSuperuser,
        user_service: UserServiceDep,
        _=Depends(permission_checker(PermissionCode.USER_UPDATE.value))
) -> Any:
    """
    更新用户信息
    """
    try:
        print(f"🎯 API端点: 开始更新用户 {id}")
        print(f"📨 请求数据: {user_update.model_dump(exclude_unset=True)}")

        user_info = await user_service.update_user(id, user_update)
        return ApiResponse.success(data=user_info, msg="用户信息更新成功")
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户信息更新失败: {str(e)}")


@router.post(
    "/delete/{ids}",
    response_model=ApiResponse[dict],
    summary="删除用户（支持批量）",
    description="删除指定用户或多个用户，多个用户ID以英文逗号分隔"
)
@permission(
    code=PermissionCode.USER_DELETE.value,
    name="用户删除权限",
    description="删除用户的核心权限"
)
@inject
async def delete_user(
        ids: str,
        current_user: CurrentUser,
        # _superuser: CurrentSuperuser,
        user_service: UserServiceDep
        # _=Depends(permission_checker(PermissionCode.USER_DELETE.value))
) -> Any:
    """
    删除用户（支持批量）

    Args:
        ids: 用户ID字符串，多个以英文逗号分隔，例如：id1,id2,id3
    """
    try:
        # 当前登录用户id
        current_user_id = current_user.id

        # 将逗号分隔的字符串转换为列表
        if not ids or not ids.strip():
            raise BadRequest(detail="用户ID不能为空")

        # 分割字符串，过滤空值
        user_ids = [user_id.strip() for user_id in ids.split(',') if user_id.strip()]

        if not user_ids:
            raise BadRequest(detail="没有提供有效的用户ID")

        # 检查是否包含当前登录用户的ID
        if str(current_user_id) in user_ids:
            return ApiResponse.error(
                data={
                },
                msg=f"不能删除当前登录用户"
            )

        # 调用服务层的批量删除方法
        deleted_count = await user_service.batch_soft_delete(user_ids)

        return ApiResponse.success(
            data={
                "deleted": True,
                "deleted_count": deleted_count,
                "total_ids": len(user_ids)
            },
            msg=f"成功删除 {deleted_count} 个用户"
        )
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户删除失败: {str(e)}")


# ============ 扩展功能接口 ============
@router.post(
    "/create-with-roles",
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


@router.post(
    "/assign-roles/{id}",
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
    id: str,  # 路径参数
    role_ids: List[str],  # 请求体
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
) -> Any:
    return await user_service.assign_roles(id, role_ids)


@router.post(
    "/reset-password/{id}",
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
    id: str,  # 路径参数
    new_password: str,  # 请求体
    _superuser: CurrentSuperuser,  # 无默认值
    user_service: UserServiceDep,  # 无默认值
    _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
) -> Any:
    return await user_service.update_password(id, new_password)


# ============ 用户回收站相关接口 ============
@router.get(
    "/recycle-bin",
    response_model=ApiResponse,
    summary="获取回收站用户列表",
    description="获取已删除的用户列表，仅超级管理员可访问"
)
@permission(
    code=PermissionCode.USER_RECYCLE_BIN_VIEW.value,
    name="回收站查看权限",
    description="查看已删除用户列表"
)
@inject
async def list_deleted_users(
        user_service: UserServiceDep,
        dept_service: DeptServiceDep,
        # 分页参数
        pageNum: int = Query(1, description="页码", ge=1),
        pageSize: int = Query(10, description="每页数量", ge=1, le=100),
        # 排序参数
        field: Optional[str] = Query(None, description="排序字段"),
        direction: Optional[str] = Query("DESC", description="排序方向（ASC-正序；DESC-反序）"),
        # 过滤参数 - 支持查询已删除用户（默认已包含is_deleted=1）
        username__like: Optional[str] = Query(None, description="用户名（模糊匹配）"),
        nickname__like: Optional[str] = Query(None, description="昵称（模糊匹配）"),
        keywords: Optional[str] = Query(None, description="综合搜索（用户名/昵称/邮箱/手机号）"),
        create_time_start: Optional[date] = Query(None, alias="createTime[0]", description="创建时间起始（格式：YYYY-MM-DD）"),
        create_time_end: Optional[date] = Query(None, alias="createTime[1]", description="创建时间结束（格式：YYYY-MM-DD）"),
        mobile__like: Optional[str] = Query(None, description="手机号模糊搜索"),
        email__like: Optional[str] = Query(None, description="邮箱模糊搜索"),
        deptId: Optional[str] = Query(None, description="部门ID，筛选该部门及其所有子部门的用户")
) -> Any:
    """
    获取回收站用户列表

    说明：
    1. 默认只查询已删除的用户（is_deleted=1）
    2. 支持与其他过滤条件组合查询
    3. 排序和分页与普通用户列表一致
    """
    try:
        print("🔵 ===== 回收站用户列表接口被调用 =====")

        # 计算分页偏移量
        offset = (pageNum - 1) * pageSize

        # 构建过滤字典
        filters = {}

        # 如果存在deptId，获取部门ID列表
        if deptId:
            try:
                dept_ids = await dept_service.get_dept_and_sub_dept_ids(deptId)
                if dept_ids:
                    filters["dept_id__in"] = dept_ids
                    print(f"🔍 回收站部门筛选条件: dept_id__in={dept_ids}")
            except Exception as e:
                print(f"⚠️ 获取部门ID列表失败: {str(e)}")
                filters["dept_id__eq"] = deptId

        # 处理排序参数
        if field:
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
            # 默认排序：按删除时间降序（TODO: 如果有delete_time字段可以修改）
            filters["sort_field"] = "create_time"
            filters["sort_direction"] = "DESC"

        # 模糊查询
        if username__like is not None:
            filters["username__like"] = username__like

        if nickname__like is not None:
            filters["nickname__like"] = nickname__like

        if mobile__like is not None:
            filters["mobile__like"] = mobile__like

        if email__like is not None:
            filters["email__like"] = email__like

        # 多字段关键词搜索
        if keywords and keywords.strip():
            filters["keywords"] = keywords.strip()

        # 创建时间范围
        time_range = {}
        if create_time_start:
            time_range["start"] = create_time_start
        if create_time_end:
            time_range["end"] = create_time_end

        if time_range:
            filters["create_time_range"] = time_range

        # 记录开始时间
        import time
        start_time = time.time()

        # 并行执行数据获取
        user_future = user_service.list_deleted_users(
            offset=offset,
            limit=pageSize,
            filters=filters
        )

        dept_future = dept_service.get_dept_options_map()

        user_result, dept_map = await asyncio.gather(
            user_future,
            dept_future,
            return_exceptions=True
        )

        # 检查异常
        if isinstance(user_result, Exception):
            raise user_result

        if isinstance(dept_map, Exception):
            dept_map = {}

        # 解包用户结果
        users, total = user_result

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
            msg="获取回收站用户列表成功"
        )

    except Exception as e:
        print(f"❌ 获取回收站用户列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取回收站用户列表失败: {str(e)}")


@router.post(
    "/restore/{id}",
    response_model=ApiResponse[dict],
    summary="恢复用户",
    description="将已删除的用户恢复到正常状态"
)
@permission(
    code=PermissionCode.USER_RECYCLE_BIN_RESTORE.value,
    name="用户恢复权限",
    description="恢复已删除用户"
)
@inject
async def restore_user(
        id: str,
        user_service: UserServiceDep#,
        # _ = Depends(permission_checker(PermissionCode.USER_UPDATE.value))  # 有默认值
) -> Any:
    """
    恢复已删除的用户

    注意：
    1. 只能恢复已删除的用户
    2. 恢复后用户的is_deleted字段设为0
    3. 恢复后用户可以正常登录和使用系统
    """
    try:
        print(f"🎯 API端点: 开始恢复用户 {id}")

        # 调用服务层恢复用户
        user_info = await user_service.restore_user(id)

        return ApiResponse.success(
            data=user_info,
            msg=f"用户 '{id}' 恢复成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"用户恢复失败: {str(e)}")


# ============ 测试接口 ============
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