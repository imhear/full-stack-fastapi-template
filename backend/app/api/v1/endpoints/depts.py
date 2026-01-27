# app/api/v1/endpoints/depts.py
"""
部门API端点
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from dependency_injector.wiring import inject
from typing import Any, List, Optional
from uuid import UUID
from fastapi.responses import JSONResponse

from app.schemas.responses import ApiResponse
from app.enums.sys_permissions import PermissionCode
from app.utils.permission_decorators import permission
from app.utils.permission_checker import permission_checker
from app.api.deps import CurrentSuperuser, CurrentUser,DeptServiceDep  # 仅超级用户可操作
from app.services.sys_dept_service import DeptService
from app.di.container import Container

router = APIRouter(prefix="/depts", tags=["部门管理"])


# 依赖注入函数
# async def get_dept_service() -> DeptService:
#     """获取部门服务实例"""
#     container = Container()
#     dept_repository = container.dept_repository()
#     async_db_session = container.async_db_session()
#     return DeptService(dept_repository, async_db_session)


@router.get(
    "/options",
    response_model=ApiResponse,
    summary="部门下拉选项",
    description="获取部门树形下拉选项，仅返回启用状态的部门"
)
@inject
async def get_dept_options(
        dept_service: DeptServiceDep
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
        print("🔵 ===== 部门下拉选项接口被调用 =====")

        # 调试1：检查传入的dept_service类型
        print(f"🔍 调试1: dept_service 类型: {type(dept_service)}")
        print(f"🔍 调试1: dept_service 内容: {dept_service}")

        # 调试2：检查是否有get_dept_options方法
        if hasattr(dept_service, 'get_dept_options'):
            print("✅ 调试2: dept_service 有 get_dept_options 方法")
        else:
            print("❌ 调试2: dept_service 没有 get_dept_options 方法")
            print(
                f"🔍 调试2: dept_service 的所有方法: {[method for method in dir(dept_service) if not method.startswith('_')]}")

        # 获取部门选项
        dept_options = await dept_service.get_dept_options()

        print(f"✅ 获取部门选项成功: 返回{len(dept_options)}个部门")

        # return JSONResponse({
        #     "code": "00000",
        #     "data": dept_options,
        #     "msg": "获取部门选项成功"
        # })
        #
        return ApiResponse.success(
            data=dept_options,
            msg="获取字典项选项成功"
        )

    except Exception as e:
        print(f"❌ 获取部门选项失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取部门选项失败: {str(e)}")


@router.get(
    "/tree",
    response_model=ApiResponse,
    summary="部门树形结构",
    description="获取完整的部门树形结构"
)
@permission(
    code=PermissionCode.DEPT_READ.value,
    name="部门查询权限",
    description="查看部门树形结构"
)
@inject
async def get_dept_tree(
        dept_service: DeptServiceDep,
        _current_user: CurrentUser = None,
        _=Depends(permission_checker(PermissionCode.DEPT_READ.value))
) -> Any:
    """
    获取部门树形结构
    """
    try:
        dept_tree = await dept_service.get_dept_tree()
        return JSONResponse({
            "code": "00000",
            "data": dept_tree,
            "msg": "获取部门树成功"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取部门树失败: {str(e)}")


# 以下为其他部门管理接口，可以根据需要逐步实现

@router.get(
    "/",
    response_model=ApiResponse,
    summary="部门列表",
    description="获取部门列表，支持分页和搜索"
)
@permission(
    code=PermissionCode.DEPT_READ.value,
    name="部门查询权限",
    description="查看部门列表"
)
@inject
async def list_depts(
        dept_service: DeptServiceDep,
        pageNum: int = Query(1, description="页码", ge=1),
        pageSize: int = Query(10, description="每页数量", ge=1, le=100),
        keywords: Optional[str] = Query(None, description="部门名称关键词"),
        status: Optional[int] = Query(None, description="状态（1启用 0停用）"),

        _current_user: CurrentUser = None,
        _=Depends(permission_checker(PermissionCode.DEPT_READ.value))
) -> Any:
    """
    获取部门列表（待实现）
    """
    # TODO: 实现部门列表接口
    return JSONResponse({
        "code": "00000",
        "data": {
            "data": [],
            "page": {
                "total": 0,
                "pageNum": pageNum,
                "pageSize": pageSize
            }
        },
        "msg": "待实现"
    })


@router.post(
    "/",
    response_model=ApiResponse,
    summary="创建部门",
    description="创建新部门"
)
@permission(
    code=PermissionCode.DEPT_CREATE.value,
    name="部门创建权限",
    description="创建新部门"
)
@inject
async def create_dept(
        dept_service: DeptServiceDep,
        _superuser: CurrentSuperuser = None,
        _=Depends(permission_checker(PermissionCode.DEPT_CREATE.value))
) -> Any:
    """
    创建部门（待实现）
    """
    # TODO: 实现创建部门接口
    return JSONResponse({
        "code": "00000",
        "data": {},
        "msg": "待实现"
    })