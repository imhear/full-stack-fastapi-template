"""
数据字典服务层
backend/app/services/sys_dict_service.py
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import SysDict, SysDictItem
from app.repositories.sys_dict_repository import DictRepository
from app.schemas.sys_dict import (
    DictTypeCreate, DictTypeUpdate, DictTypeOut, DictTypeList,
    DictItemCreate, DictItemUpdate, DictItemOut, DictItemList,
    DictItemOption, DictTypeWithItems
)
from app.core.exceptions import ResourceNotFound, BadRequest
from app.services.redis_service import RedisService


class DictService:
    """
    数据字典服务层
    遵循用户模块的设计原则：业务逻辑和数据转换
    """

    def __init__(
            self,
            dict_repository: DictRepository,
            async_db_session: AsyncSession,
            redis_service: RedisService
    ):
        self.dict_repository = dict_repository
        self.async_db_session = async_db_session
        self.redis_service = redis_service

    # ==================== 字典类型管理 ====================

    async def get_dict_type_by_id(self, dict_type_id: str) -> DictTypeOut:
        """根据ID获取字典类型"""
        dict_type = await self.dict_repository.get_dict_type_by_id(dict_type_id)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典类型ID '{dict_type_id}' 不存在")
        return self._convert_dict_type_to_out(dict_type)

    async def get_dict_type_by_code(self, dict_code: str) -> DictTypeOut:
        """根据编码获取字典类型"""
        dict_type = await self.dict_repository.get_dict_type_by_code(dict_code)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典编码 '{dict_code}' 不存在")
        return self._convert_dict_type_to_out(dict_type)

    async def list_dict_types(
            self,
            page: int = 1,
            size: int = 10,
            status: Optional[int] = None,
            name: Optional[str] = None,
            dict_code: Optional[str] = None
    ) -> DictTypeList:
        """分页查询字典类型列表"""
        offset = (page - 1) * size
        dict_types, total = await self.dict_repository.list_dict_types(
            offset=offset,
            limit=size,
            status=status,
            name_like=name,
            dict_code_like=dict_code
        )

        items = [self._convert_dict_type_to_out(dict_type) for dict_type in dict_types]
        return DictTypeList(items=items, total=total)

    async def create_dict_type(self, dict_type_in: DictTypeCreate) -> DictTypeOut:
        """创建字典类型"""
        # 检查字典编码是否已存在
        if await self.dict_repository.check_dict_code_exists(dict_type_in.dict_code):
            raise BadRequest(detail=f"字典编码 '{dict_type_in.dict_code}' 已存在")

        # 创建字典类型对象
        dict_type = SysDict(
            dict_code=dict_type_in.dict_code,
            name=dict_type_in.name,
            status=dict_type_in.status,
            remark=dict_type_in.remark
        )

        async with self.dict_repository.transaction() as session:
            dict_type = await self.dict_repository.create_dict_type(dict_type, session)

        # 清除缓存
        await self._clear_dict_cache(dict_type.dict_code)

        return self._convert_dict_type_to_out(dict_type)

    async def update_dict_type(self, dict_type_id: str, dict_type_update: DictTypeUpdate) -> DictTypeOut:
        """更新字典类型"""
        dict_type = await self.dict_repository.get_dict_type_by_id(dict_type_id)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典类型ID '{dict_type_id}' 不存在")

        # 检查字典编码是否重复（如果修改了编码）
        if dict_type_update.dict_code and dict_type_update.dict_code != dict_type.dict_code:
            if await self.dict_repository.check_dict_code_exists(dict_type_update.dict_code):
                raise BadRequest(detail=f"字典编码 '{dict_type_update.dict_code}' 已存在")

        # 更新字段
        update_data = dict_type_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(dict_type, key, value)

        async with self.dict_repository.transaction() as session:
            updated_dict_type = await self.dict_repository.update_dict_type(dict_type, session)

        # 如果修改了字典编码，清除新旧两个缓存
        if dict_type_update.dict_code and dict_type_update.dict_code != dict_type.dict_code:
            await self._clear_dict_cache(dict_type.dict_code)
        await self._clear_dict_cache(updated_dict_type.dict_code)

        return self._convert_dict_type_to_out(updated_dict_type)

    async def delete_dict_type(self, dict_type_id: str) -> None:
        """删除字典类型"""
        dict_type = await self.dict_repository.get_dict_type_by_id(dict_type_id)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典类型ID '{dict_type_id}' 不存在")

        # 检查是否有字典项
        items = await self.dict_repository.get_dict_items_by_code(dict_type.dict_code, only_enabled=False)
        if items:
            raise BadRequest(detail=f"字典类型 '{dict_type.dict_code}' 下存在字典项，请先删除字典项")

        async with self.dict_repository.transaction() as session:
            success = await self.dict_repository.delete_dict_type(dict_type_id, session)
            if not success:
                raise ResourceNotFound(detail=f"字典类型ID '{dict_type_id}' 删除失败")

        # 清除缓存
        await self._clear_dict_cache(dict_type.dict_code)

    # ==================== 字典项管理 ====================

    async def get_dict_item_by_id(self, item_id: str) -> DictItemOut:
        """根据ID获取字典项"""
        dict_item = await self.dict_repository.get_dict_item_by_id(item_id)
        if not dict_item:
            raise ResourceNotFound(detail=f"字典项ID '{item_id}' 不存在")
        return self._convert_dict_item_to_out(dict_item)

    async def get_dict_items_by_code(
            self,
            dict_code: str,
            status: Optional[int] = None
    ) -> List[DictItemOut]:
        """根据字典编码获取字典项列表"""
        # 检查字典类型是否存在
        dict_type = await self.dict_repository.get_dict_type_by_code(dict_code)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典编码 '{dict_code}' 不存在")

        dict_items = await self.dict_repository.get_dict_items_by_code(
            dict_code=dict_code,
            status=status,
            only_enabled=False
        )

        return [self._convert_dict_item_to_out(item) for item in dict_items]

    async def get_dict_item_options(self, dict_code: str) -> List[DictItemOption]:
        """
        获取字典项选项（用于前端下拉框）
        支持缓存，提高性能
        """
        cache_key = f"dict:options:{dict_code}"

        # 尝试从缓存获取
        cached_options = await self.redis_service.get(cache_key)
        if cached_options:
            return [DictItemOption(**item) for item in cached_options]

        # 检查字典类型是否存在
        dict_type = await self.dict_repository.get_dict_type_by_code(dict_code)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典编码 '{dict_code}' 不存在")

        # 从数据库获取（只获取启用的项）
        dict_items = await self.dict_repository.get_dict_items_for_options(
            dict_code=dict_code,
            status=1  # 只获取启用的项
        )

        options = [DictItemOption(**item) for item in dict_items]

        # 缓存结果（5分钟过期）
        if options:
            await self.redis_service.setex(
                cache_key,
                300,  # 5分钟
                [item.model_dump() for item in options]
            )

        return options

    async def list_dict_items(
            self,
            dict_code: Optional[str] = None,
            page: int = 1,
            size: int = 10,
            status: Optional[int] = None,
            label: Optional[str] = None,
            value: Optional[str] = None
    ) -> DictItemList:
        """分页查询字典项列表"""
        offset = (page - 1) * size

        dict_items, total = await self.dict_repository.list_dict_items(
            dict_code=dict_code,
            offset=offset,
            limit=size,
            status=status,
            label_like=label,
            value_like=value
        )

        items = [self._convert_dict_item_to_out(item) for item in dict_items]
        return DictItemList(items=items, total=total)

    async def create_dict_item(self, dict_item_in: DictItemCreate) -> DictItemOut:
        """创建字典项"""
        # 检查字典类型是否存在
        dict_type = await self.dict_repository.get_dict_type_by_code(dict_item_in.dict_code)
        if not dict_type:
            raise ResourceNotFound(detail=f"字典编码 '{dict_item_in.dict_code}' 不存在")

        # 检查字典项值是否重复
        if await self.dict_repository.check_value_exists(
                dict_item_in.dict_code,
                dict_item_in.value
        ):
            raise BadRequest(detail=f"字典项值 '{dict_item_in.value}' 已存在")

        # 创建字典项对象
        dict_item = SysDictItem(
            dict_code=dict_item_in.dict_code,
            value=dict_item_in.value,
            label=dict_item_in.label,
            tag_type=dict_item_in.tag_type,
            status=dict_item_in.status,
            sort=dict_item_in.sort,
            remark=dict_item_in.remark
        )

        async with self.dict_repository.transaction() as session:
            dict_item = await self.dict_repository.create_dict_item(dict_item, session)

        # 清除缓存
        await self._clear_dict_cache(dict_item.dict_code)

        return self._convert_dict_item_to_out(dict_item)

    async def update_dict_item(self, item_id: str, dict_item_update: DictItemUpdate) -> DictItemOut:
        """更新字典项"""
        dict_item = await self.dict_repository.get_dict_item_by_id(item_id)
        if not dict_item:
            raise ResourceNotFound(detail=f"字典项ID '{item_id}' 不存在")

        update_data = dict_item_update.model_dump(exclude_unset=True)

        # 检查字典项值是否重复（如果修改了值）
        if 'value' in update_data and update_data['value'] != dict_item.value:
            if await self.dict_repository.check_value_exists(
                    dict_item.dict_code,
                    update_data['value'],
                    exclude_item_id=item_id
            ):
                raise BadRequest(detail=f"字典项值 '{update_data['value']}' 已存在")

        # 更新字段
        for key, value in update_data.items():
            if value is not None:
                setattr(dict_item, key, value)

        async with self.dict_repository.transaction() as session:
            updated_dict_item = await self.dict_repository.update_dict_item(dict_item, session)

        # 清除缓存
        await self._clear_dict_cache(updated_dict_item.dict_code)

        return self._convert_dict_item_to_out(updated_dict_item)

    async def delete_dict_item(self, item_id: str) -> None:
        """删除字典项"""
        dict_item = await self.dict_repository.get_dict_item_by_id(item_id)
        if not dict_item:
            raise ResourceNotFound(detail=f"字典项ID '{item_id}' 不存在")

        async with self.dict_repository.transaction() as session:
            success = await self.dict_repository.delete_dict_item(item_id, session)
            if not success:
                raise ResourceNotFound(detail=f"字典项ID '{item_id}' 删除失败")

        # 清除缓存
        await self._clear_dict_cache(dict_item.dict_code)

    # ==================== 辅助方法 ====================

    def _convert_dict_type_to_out(self, dict_type: SysDict) -> DictTypeOut:
        """转换字典类型为输出模型"""
        return DictTypeOut(
            id=str(dict_type.id),
            dict_code=dict_type.dict_code,
            name=dict_type.name,
            status=dict_type.status,
            remark=dict_type.remark,
            create_time=dict_type.create_time,
            update_time=dict_type.update_time
        )

    def _convert_dict_item_to_out(self, dict_item: SysDictItem) -> DictItemOut:
        """转换字典项为输出模型"""
        return DictItemOut(
            id=str(dict_item.id),
            dict_code=dict_item.dict_code,
            value=dict_item.value,
            label=dict_item.label,
            tag_type=dict_item.tag_type,
            status=dict_item.status,
            sort=dict_item.sort,
            remark=dict_item.remark,
            create_time=dict_item.create_time,
            update_time=dict_item.update_time
        )

    async def _clear_dict_cache(self, dict_code: str) -> None:
        """清除字典缓存"""
        cache_key = f"dict:options:{dict_code}"
        await self.redis_service.delete(cache_key)