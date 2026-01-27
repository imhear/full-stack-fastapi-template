"""
数据字典API端点
backend/app/api/v1/endpoints/dicts.py
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from dependency_injector.wiring import inject
from typing import Any, List, Optional
from fastapi.responses import JSONResponse

from app.schemas.responses import ApiResponse
from app.core.exceptions import BadRequest, ResourceNotFound
from app.schemas.sys_dict import (
    DictTypeCreate, DictTypeUpdate, DictItemCreate, DictItemUpdate,
    DictItemOption
)
from app.enums.sys_permissions import PermissionCode
from app.utils.permission_decorators import permission
from app.utils.permission_checker import permission_checker
from app.api.deps import CurrentSuperuser, CurrentUser, DictServiceDep

router = APIRouter(prefix="/dicts", tags=["dicts"])


# ==================== 字典项公共接口（无需权限） ====================

@router.get(
    "/{dict_code}/items",
    response_model=ApiResponse[List[DictItemOption]],
    summary="获取字典项列表",
    description="根据字典编码获取字典项列表（公共接口）"
)
@inject
async def get_dict_items(
        dict_code: str = Path(..., description="字典编码", example="gender"),
        dict_service: DictServiceDep = None
) -> Any:
    """
    获取字典项列表

    用于前端下拉框等场景，默认只返回启用的字典项

    响应格式：
    {
        "code": "00000",
        "data": [
            {
                "value": "1",
                "label": "男",
                "tagType": "success"
            }
        ],
        "msg": "操作成功"
    }
    """
    try:
        print(f"🔵 ===== 获取字典项接口被调用 ===== dict_code={dict_code}")

        # 获取字典项选项
        options = await dict_service.get_dict_item_options(dict_code)

        print(f"✅ 获取字典项成功: dict_code={dict_code}, count={len(options)}")

        return ApiResponse.success(
            data=options,
            msg="获取字典项成功"
        )

    except ResourceNotFound as e:
        print(f"❌ 字典编码不存在: {dict_code}, error={str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 获取字典项失败: dict_code={dict_code}, error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字典项失败: {str(e)}")


@router.get(
    "/{dict_code}/items/options",
    response_model=ApiResponse[List[DictItemOption]],
    summary="获取字典项选项（兼容旧接口）",
    description="兼容旧接口，功能同 /{dict_code}/items"
)
@inject
async def get_dict_items_options(
        dict_code: str = Path(..., description="字典编码", example="gender"),
        dict_service: DictServiceDep = None
) -> Any:
    """
    获取字典项选项（兼容旧接口）

    这个接口是为了兼容前端可能存在的旧调用
    """
    try:
        print(f"🔵 ===== 获取字典项选项接口被调用（兼容版） ===== dict_code={dict_code}")

        # 调用相同的业务逻辑
        options = await dict_service.get_dict_item_options(dict_code)

        print(f"✅ 获取字典项选项成功: dict_code={dict_code}, count={len(options)}")

        return ApiResponse.success(
            data=options,
            msg="获取字典项选项成功"
        )

    except ResourceNotFound as e:
        print(f"❌ 字典编码不存在: {dict_code}, error={str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 获取字典项选项失败: dict_code={dict_code}, error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字典项选项失败: {str(e)}")


# ==================== 字典类型管理接口（需要权限） ====================

@router.get(
    "/types/",
    response_model=ApiResponse,
    summary="获取字典类型列表",
    description="分页获取字典类型列表（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_READ.value,
    name="数据字典查询权限",
    description="查看数据字典"
)
@inject
async def list_dict_types(
        dict_service: DictServiceDep,
        page: int = Query(1, description="页码", ge=1),
        size: int = Query(10, description="每页数量", ge=1, le=100),
        status: Optional[int] = Query(None, description="状态（0:正常;1:禁用）"),
        name: Optional[str] = Query(None, description="字典名称（模糊匹配）"),
        dict_code: Optional[str] = Query(None, description="字典编码（模糊匹配）"),
        _superuser: CurrentSuperuser = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_READ.value))
) -> Any:
    """分页查询字典类型列表"""
    try:
        print(f"🔵 ===== 获取字典类型列表接口被调用 ===== page={page}, size={size}")

        dict_types = await dict_service.list_dict_types(
            page=page,
            size=size,
            status=status,
            name=name,
            dict_code=dict_code
        )

        print(f"✅ 获取字典类型列表成功: total={dict_types.total}")

        return ApiResponse.success(
            data={
                "data": [dict_type.model_dump() for dict_type in dict_types.items],
                "page": {
                    "total": dict_types.total,
                    "pageNum": page,
                    "pageSize": size
                }
            },
            msg="获取字典类型列表成功"
        )

    except Exception as e:
        print(f"❌ 获取字典类型列表失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字典类型列表失败: {str(e)}")


@router.get(
    "/types/{dict_type_id}",
    response_model=ApiResponse,
    summary="获取字典类型详情",
    description="根据ID获取字典类型详情（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_READ.value,
    name="数据字典查询权限",
    description="查看数据字典"
)
@inject
async def get_dict_type(
        dict_type_id: str = Path(..., description="字典类型ID"),
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_READ.value))
) -> Any:
    """获取字典类型详情"""
    try:
        print(f"🔵 ===== 获取字典类型详情接口被调用 ===== dict_type_id={dict_type_id}")

        dict_type = await dict_service.get_dict_type_by_id(dict_type_id)

        print(f"✅ 获取字典类型详情成功: dict_type_id={dict_type_id}")

        return ApiResponse.success(
            data=dict_type.model_dump(),
            msg="获取字典类型详情成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 获取字典类型详情失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字典类型详情失败: {str(e)}")


@router.post(
    "/types/",
    response_model=ApiResponse,
    summary="创建字典类型",
    description="创建新的字典类型（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_CREATE.value,
    name="数据字典创建权限",
    description="创建数据字典"
)
@inject
async def create_dict_type(
        dict_type_in: DictTypeCreate,
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_CREATE.value))
) -> Any:
    """创建字典类型"""
    try:
        print(f"🔵 ===== 创建字典类型接口被调用 ===== dict_code={dict_type_in.dict_code}")

        dict_type = await dict_service.create_dict_type(dict_type_in)

        print(f"✅ 创建字典类型成功: dict_code={dict_type.dict_code}")

        return ApiResponse.success(
            data=dict_type.model_dump(),
            msg="创建字典类型成功"
        )

    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 创建字典类型失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建字典类型失败: {str(e)}")


@router.put(
    "/types/{dict_type_id}",
    response_model=ApiResponse,
    summary="更新字典类型",
    description="更新字典类型信息（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_UPDATE.value,
    name="数据字典更新权限",
    description="更新数据字典"
)
@inject
async def update_dict_type(
        dict_type_id: str,
        dict_type_update: DictTypeUpdate,
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_UPDATE.value))
) -> Any:
    """更新字典类型"""
    try:
        print(f"🔵 ===== 更新字典类型接口被调用 ===== dict_type_id={dict_type_id}")

        dict_type = await dict_service.update_dict_type(dict_type_id, dict_type_update)

        print(f"✅ 更新字典类型成功: dict_type_id={dict_type_id}")

        return ApiResponse.success(
            data=dict_type.model_dump(),
            msg="更新字典类型成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 更新字典类型失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新字典类型失败: {str(e)}")


@router.delete(
    "/types/{dict_type_id}",
    response_model=ApiResponse,
    summary="删除字典类型",
    description="删除字典类型（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_DELETE.value,
    name="数据字典删除权限",
    description="删除数据字典"
)
@inject
async def delete_dict_type(
        dict_type_id: str,
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_DELETE.value))
) -> Any:
    """删除字典类型"""
    try:
        print(f"🔵 ===== 删除字典类型接口被调用 ===== dict_type_id={dict_type_id}")

        await dict_service.delete_dict_type(dict_type_id)

        print(f"✅ 删除字典类型成功: dict_type_id={dict_type_id}")

        return ApiResponse.success(
            data=None,
            msg="删除字典类型成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 删除字典类型失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除字典类型失败: {str(e)}")


# ==================== 字典项管理接口（需要权限） ====================

@router.get(
    "/items/",
    response_model=ApiResponse,
    summary="获取字典项列表",
    description="分页获取字典项列表（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_READ.value,
    name="数据字典查询权限",
    description="查看数据字典"
)
@inject
async def list_dict_items(
        dict_service: DictServiceDep,
        page: int = Query(1, description="页码", ge=1),
        size: int = Query(10, description="每页数量", ge=1, le=100),
        dict_code: Optional[str] = Query(None, description="字典编码"),
        status: Optional[int] = Query(None, description="状态（1-正常，0-禁用）"),
        label: Optional[str] = Query(None, description="标签（模糊匹配）"),
        value: Optional[str] = Query(None, description="值（模糊匹配）"),
        _superuser: CurrentSuperuser = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_READ.value))
) -> Any:
    """分页查询字典项列表"""
    try:
        print(f"🔵 ===== 获取字典项列表接口被调用 ===== page={page}, size={size}, dict_code={dict_code}")

        dict_items = await dict_service.list_dict_items(
            dict_code=dict_code,
            page=page,
            size=size,
            status=status,
            label=label,
            value=value
        )

        print(f"✅ 获取字典项列表成功: total={dict_items.total}")

        return ApiResponse.success(
            data={
                "data": [dict_item.model_dump() for dict_item in dict_items.items],
                "page": {
                    "total": dict_items.total,
                    "pageNum": page,
                    "pageSize": size
                }
            },
            msg="获取字典项列表成功"
        )

    except Exception as e:
        print(f"❌ 获取字典项列表失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字典项列表失败: {str(e)}")


@router.get(
    "/items/{item_id}",
    response_model=ApiResponse,
    summary="获取字典项详情",
    description="根据ID获取字典项详情（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_READ.value,
    name="数据字典查询权限",
    description="查看数据字典"
)
@inject
async def get_dict_item(
        item_id: str = Path(..., description="字典项ID"),
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_READ.value))
) -> Any:
    """获取字典项详情"""
    try:
        print(f"🔵 ===== 获取字典项详情接口被调用 ===== item_id={item_id}")

        dict_item = await dict_service.get_dict_item_by_id(item_id)

        print(f"✅ 获取字典项详情成功: item_id={item_id}")

        return ApiResponse.success(
            data=dict_item.model_dump(),
            msg="获取字典项详情成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 获取字典项详情失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字典项详情失败: {str(e)}")


@router.post(
    "/items/",
    response_model=ApiResponse,
    summary="创建字典项",
    description="创建新的字典项（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_CREATE.value,
    name="数据字典创建权限",
    description="创建数据字典"
)
@inject
async def create_dict_item(
        dict_item_in: DictItemCreate,
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_CREATE.value))
) -> Any:
    """创建字典项"""
    try:
        print(f"🔵 ===== 创建字典项接口被调用 ===== dict_code={dict_item_in.dict_code}, value={dict_item_in.value}")

        dict_item = await dict_service.create_dict_item(dict_item_in)

        print(f"✅ 创建字典项成功: dict_code={dict_item.dict_code}, value={dict_item.value}")

        return ApiResponse.success(
            data=dict_item.model_dump(),
            msg="创建字典项成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 创建字典项失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建字典项失败: {str(e)}")


@router.put(
    "/items/{item_id}",
    response_model=ApiResponse,
    summary="更新字典项",
    description="更新字典项信息（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_UPDATE.value,
    name="数据字典更新权限",
    description="更新数据字典"
)
@inject
async def update_dict_item(
        item_id: str,
        dict_item_update: DictItemUpdate,
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_UPDATE.value))
) -> Any:
    """更新字典项"""
    try:
        print(f"🔵 ===== 更新字典项接口被调用 ===== item_id={item_id}")

        dict_item = await dict_service.update_dict_item(item_id, dict_item_update)

        print(f"✅ 更新字典项成功: item_id={item_id}")

        return ApiResponse.success(
            data=dict_item.model_dump(),
            msg="更新字典项成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 更新字典项失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新字典项失败: {str(e)}")


@router.delete(
    "/items/{item_id}",
    response_model=ApiResponse,
    summary="删除字典项",
    description="删除字典项（需要权限）"
)
@permission(
    code=PermissionCode.SYSTEM_DICT_DELETE.value,
    name="数据字典删除权限",
    description="删除数据字典"
)
@inject
async def delete_dict_item(
        item_id: str,
        _superuser: CurrentSuperuser = None,
        dict_service: DictServiceDep = None,
        _=Depends(permission_checker(PermissionCode.SYSTEM_DICT_DELETE.value))
) -> Any:
    """删除字典项"""
    try:
        print(f"🔵 ===== 删除字典项接口被调用 ===== item_id={item_id}")

        await dict_service.delete_dict_item(item_id)

        print(f"✅ 删除字典项成功: item_id={item_id}")

        return ApiResponse.success(
            data=None,
            msg="删除字典项成功"
        )

    except ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 删除字典项失败: error={str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除字典项失败: {str(e)}")