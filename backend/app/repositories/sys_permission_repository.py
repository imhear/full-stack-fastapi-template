"""
权限模块数据访问层
backend/app/db/repositories/permission_repository.py
上次更新：2025/12/1
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from contextlib import asynccontextmanager
from typing import Set, List, Optional, AsyncGenerator

from app.models import SysUser, sys_user_role, SysPermission, sys_role_permission

logger = logging.getLogger(__name__)


class PermissionRepository:
    """权限Repo层：标准事务上下文实现"""
    def __init__(self, async_session_factory: sessionmaker):
        self.async_session_factory = async_session_factory

    # ------------------------------
    # 标准异步事务上下文（同UserRepo）
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
    # 查询类方法
    # ------------------------------
    async def get_by_id(self, perm_id: str) -> Optional[SysPermission]:
        """按ID查询权限"""
        async with self.transaction() as session:
            stmt = select(SysPermission).where(SysPermission.id == perm_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[SysPermission]:
        """按权限编码查询（编码唯一）"""
        async with self.transaction() as session:
            stmt = select(SysPermission).where(SysPermission.code == code)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_existing_ids(self, permission_ids: List[str]) -> Set[str]:
        """校验权限ID有效性，返回存在的ID集合"""
        if not permission_ids:
            logger.debug("No permission IDs provided, returning empty set")
            return set()

        async with self.transaction() as session:
            stmt = select(SysPermission.id).where(SysPermission.id.in_(permission_ids))
            result = await session.execute(stmt)
            existing_ids = {row[0] for row in result.all()}

        # 日志提示：若存在无效ID，便于排查
        invalid_ids = set(permission_ids) - existing_ids
        if invalid_ids:
            logger.warning(f"Invalid permission IDs: {invalid_ids}")

        return existing_ids

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户所有权限编码（含角色继承的权限）"""
        async with self.transaction() as session:
            # 关联查询：User → user_roles → Role → role_permissions → Permission
            stmt = (
                select(SysPermission.code)
                .select_from(SysUser)
                .join(sys_user_role, SysUser.id == sys_user_role.c.user_id)
                .join(sys_role_permission, sys_user_role.c.role_id == sys_role_permission.c.role_id)
                .join(SysPermission, sys_role_permission.c.permission_id == SysPermission.id)
                .where(
                    SysUser.id == user_id,
                    SysPermission.is_active == True,  # 只取激活的权限
                    SysUser.is_active == True         # 只取激活的用户
                )
            )
            result = await session.execute(stmt)
            rows = result.all()
            return {row[0] for row in rows}  # 返回权限编码集合

    async def list_all(self, offset: int = 0, limit: int = 100) -> List[SysPermission]:
        """分页查询所有权限"""
        async with self.transaction() as session:
            stmt = (
                select(SysPermission)
                .offset(offset)
                .limit(limit)
                .order_by(SysPermission.category, SysPermission.code)  # 按分类+编码排序
            )
            result = await session.execute(stmt)
            return result.scalars().all()