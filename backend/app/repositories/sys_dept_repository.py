# app/repositories/sys_dept_repository.py
"""
部门模块数据访问层
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlmodel import select, delete, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.models import SysDept


class DeptRepository:
    """
    部门仓储层
    """

    def __init__(self, async_session_factory: sessionmaker):
        self.async_session_factory = async_session_factory

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """事务上下文管理器"""
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

    async def get_by_id(self, dept_id: UUID) -> Optional[SysDept]:
        """根据ID获取部门"""
        async with self.transaction() as session:
            stmt = select(SysDept).where(
                SysDept.id == dept_id,
                SysDept.is_deleted == 0
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[SysDept]:
        """根据编码获取部门"""
        async with self.transaction() as session:
            stmt = select(SysDept).where(
                SysDept.code == code,
                SysDept.is_deleted == 0
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_all_enabled_depts(self) -> List[SysDept]:
        """获取所有启用的部门（状态为1，未删除）"""
        async with self.transaction() as session:
            stmt = select(SysDept).where(
                SysDept.status == 1,
                SysDept.is_deleted == 0
            ).order_by(SysDept.sort, SysDept.id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_root_depts(self) -> List[SysDept]:
        """获取所有根部门（parent_id为空或0）"""
        async with self.transaction() as session:
            stmt = select(SysDept).where(
                SysDept.parent_id.is_(None),
                SysDept.status == 1,
                SysDept.is_deleted == 0
            ).order_by(SysDept.sort, SysDept.id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_children_depts(self, parent_id: UUID) -> List[SysDept]:
        """获取指定父部门的所有子部门"""
        async with self.transaction() as session:
            stmt = select(SysDept).where(
                SysDept.parent_id == parent_id,
                SysDept.status == 1,
                SysDept.is_deleted == 0
            ).order_by(SysDept.sort, SysDept.id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_depts_by_tree_path_pattern(self, pattern: str) -> List[SysDept]:
        """根据tree_path模式查找部门"""
        async with self.transaction() as session:
            stmt = select(SysDept).where(SysDept.tree_path.like(pattern))
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, dept_data: Dict[str, Any], session: AsyncSession) -> SysDept:
        """创建部门"""
        db_dept = SysDept(**dept_data)
        session.add(db_dept)
        await session.flush()
        return db_dept

    async def update(self, dept: SysDept, session: AsyncSession) -> SysDept:
        """更新部门"""
        session.add(dept)
        await session.refresh(dept)
        return dept

    async def delete(self, dept_id: UUID, session: AsyncSession) -> bool:
        """删除部门（软删除）"""
        dept = await self.get_by_id(dept_id)
        if not dept:
            return False
        dept.is_deleted = 1
        session.add(dept)
        return True

    async def check_has_children(self, dept_id: UUID) -> bool:
        """检查部门是否有子部门"""
        async with self.transaction() as session:
            stmt = select(func.count(SysDept.id)).where(
                SysDept.parent_id == dept_id,
                SysDept.is_deleted == 0
            )
            result = await session.execute(stmt)
            count = result.scalar() or 0
            return count > 0

    async def check_has_users(self, dept_id: UUID) -> bool:
        """检查部门下是否有用户"""
        from app.models import SysUser
        async with self.transaction() as session:
            stmt = select(func.count(SysUser.id)).where(
                SysUser.dept_id == dept_id,
                SysUser.is_deleted == 0
            )
            result = await session.execute(stmt)
            count = result.scalar() or 0
            return count > 0