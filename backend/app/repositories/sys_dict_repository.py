"""
数据字典仓库层
backend/app/repositories/sys_dict_repository.py
"""
from sqlmodel import select, delete, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import Optional, List, AsyncGenerator, Tuple, Dict, Any
from datetime import datetime

from app.models import SysDict, SysDictItem


class DictRepository:
    """
    数据字典仓库层
    遵循用户模块的设计模式，使用事务上下文管理
    """

    def __init__(self, async_session_factory: sessionmaker):
        self.async_session_factory = async_session_factory

    # ------------------------------
    # 核心：标准异步事务上下文
    # ------------------------------
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self.async_session_factory()
        try:
            await session.begin()
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    # ------------------------------
    # 字典类型相关方法
    # ------------------------------
    async def get_dict_type_by_id(self, dict_type_id: str) -> Optional[SysDict]:
        """根据ID获取字典类型"""
        async with self.transaction() as session:
            stmt = select(SysDict).where(SysDict.id == dict_type_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_dict_type_by_code(self, dict_code: str) -> Optional[SysDict]:
        """根据编码获取字典类型"""
        async with self.transaction() as session:
            stmt = select(SysDict).where(
                SysDict.dict_code == dict_code,
                SysDict.status == 1,
                SysDict.is_deleted == 0
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def list_dict_types(
        self,
        offset: int = 0,
        limit: int = 100,
        status: Optional[int] = None,
        name_like: Optional[str] = None,
        dict_code_like: Optional[str] = None
    ) -> Tuple[List[SysDict], int]:
        """分页查询字典类型列表"""
        async with self.transaction() as session:
            # 基础查询
            stmt = select(SysDict, func.count(SysDict.id).over().label('total_count')).where(
                SysDict.is_deleted == 0
            )

            # 应用过滤条件
            if status is not None:
                stmt = stmt.filter(SysDict.status == status)

            if name_like:
                stmt = stmt.filter(SysDict.name.ilike(f"%{name_like}%"))

            if dict_code_like:
                stmt = stmt.filter(SysDict.dict_code.ilike(f"%{dict_code_like}%"))

            # 应用分页和排序
            stmt = stmt.order_by(SysDict.create_time.desc()).offset(offset).limit(limit)

            # 执行查询
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return [], 0

            dict_types = [row[0] for row in rows]
            total = rows[0].total_count if rows[0].total_count else 0

            return dict_types, total

    async def create_dict_type(self, dict_type: SysDict, session: AsyncSession) -> SysDict:
        """创建字典类型"""
        session.add(dict_type)
        await session.flush()
        return dict_type

    async def update_dict_type(self, dict_type: SysDict, session: AsyncSession) -> SysDict:
        """更新字典类型"""
        session.add(dict_type)
        await session.refresh(dict_type)
        return dict_type

    async def delete_dict_type(self, dict_type_id: str, session: AsyncSession) -> bool:
        """逻辑删除字典类型"""
        dict_type = await self.get_dict_type_by_id(dict_type_id)
        if not dict_type:
            return False
        dict_type.is_deleted = 1
        return True

    # ------------------------------
    # 字典项相关方法
    # ------------------------------
    async def get_dict_item_by_id(self, item_id: str) -> Optional[SysDictItem]:
        """根据ID获取字典项"""
        async with self.transaction() as session:
            stmt = select(SysDictItem).where(SysDictItem.id == item_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_dict_items_by_code(
        self,
        dict_code: str,
        status: Optional[int] = None,
        only_enabled: bool = True
    ) -> List[SysDictItem]:
        """根据字典编码获取字典项"""
        async with self.transaction() as session:
            stmt = select(SysDictItem).where(SysDictItem.dict_code == dict_code)

            # 默认只查询启用的项
            if only_enabled:
                stmt = stmt.filter(SysDictItem.status == 1)
            elif status is not None:
                stmt = stmt.filter(SysDictItem.status == status)

            # 按排序字段排序
            stmt = stmt.order_by(SysDictItem.sort, SysDictItem.create_time)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_dict_items_for_options(
        self,
        dict_code: str,
        status: Optional[int] = 1
    ) -> List[Dict[str, Any]]:
        """获取字典项选项（专门用于前端下拉框）"""
        async with self.transaction() as session:
            stmt = select(
                SysDictItem.value,
                SysDictItem.label,
                SysDictItem.tag_type
            ).where(
                SysDictItem.dict_code == dict_code,
                SysDictItem.status == status if status is not None else True
            ).order_by(SysDictItem.sort, SysDictItem.create_time)

            result = await session.execute(stmt)
            rows = result.all()

            # 转换为字典列表
            return [
                {
                    "value": row.value,
                    "label": row.label,
                    "tag_type": row.tag_type
                }
                for row in rows
            ]

    async def list_dict_items(
        self,
        dict_code: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
        status: Optional[int] = None,
        label_like: Optional[str] = None,
        value_like: Optional[str] = None
    ) -> Tuple[List[SysDictItem], int]:
        """分页查询字典项列表"""
        async with self.transaction() as session:
            # 基础查询
            stmt = select(SysDictItem, func.count(SysDictItem.id).over().label('total_count'))

            # 应用过滤条件
            if dict_code:
                stmt = stmt.filter(SysDictItem.dict_code == dict_code)

            if status is not None:
                stmt = stmt.filter(SysDictItem.status == status)

            if label_like:
                stmt = stmt.filter(SysDictItem.label.ilike(f"%{label_like}%"))

            if value_like:
                stmt = stmt.filter(SysDictItem.value.ilike(f"%{value_like}%"))

            # 应用分页和排序
            stmt = stmt.order_by(
                SysDictItem.dict_code,
                SysDictItem.sort,
                SysDictItem.create_time
            ).offset(offset).limit(limit)

            # 执行查询
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return [], 0

            dict_items = [row[0] for row in rows]
            total = rows[0].total_count if rows[0].total_count else 0

            return dict_items, total

    async def create_dict_item(self, dict_item: SysDictItem, session: AsyncSession) -> SysDictItem:
        """创建字典项"""
        session.add(dict_item)
        await session.flush()
        return dict_item

    async def update_dict_item(self, dict_item: SysDictItem, session: AsyncSession) -> SysDictItem:
        """更新字典项"""
        session.add(dict_item)
        await session.refresh(dict_item)
        return dict_item

    async def delete_dict_item(self, item_id: str, session: AsyncSession) -> bool:
        """删除字典项"""
        dict_item = await self.get_dict_item_by_id(item_id)
        if not dict_item:
            return False
        await session.delete(dict_item)
        return True

    async def check_dict_code_exists(self, dict_code: str) -> bool:
        """检查字典编码是否存在"""
        async with self.transaction() as session:
            stmt = select(SysDict).where(
                SysDict.dict_code == dict_code,
                SysDict.is_deleted == 0
            ).limit(1)
            result = await session.execute(stmt)
            return result.scalars().first() is not None

    async def check_value_exists(
        self,
        dict_code: str,
        value: str,
        exclude_item_id: Optional[str] = None
    ) -> bool:
        """检查字典项值是否已存在"""
        async with self.transaction() as session:
            stmt = select(SysDictItem).where(
                SysDictItem.dict_code == dict_code,
                SysDictItem.value == value
            )
            if exclude_item_id:
                stmt = stmt.filter(SysDictItem.id != exclude_item_id)
            stmt = stmt.limit(1)
            result = await session.execute(stmt)
            return result.scalars().first() is not None