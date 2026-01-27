"""
角色模块数据访问层
backend/app/db/repositories/role_repository.py
上次更新：2025/12/1
"""
from sqlmodel import select, delete, insert
from sqlalchemy.orm import sessionmaker, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from contextlib import asynccontextmanager
from typing import Optional, List, AsyncGenerator

from app.models import SysRole, sys_role_permission
from app.schemas.sys_role import RoleCreate, RoleUpdate


class RoleRepository:
    """角色Repo层：标准事务上下文实现"""
    def __init__(self, async_session_factory: sessionmaker):
        self.async_session_factory = async_session_factory

    # ------------------------------
    # 标准异步事务上下文（无修改）
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
    # 查询类方法（无修改，供外部单独查询使用）
    # ------------------------------
    async def get_by_code(self, code: str) -> Optional[SysRole]:
        """按角色编码查询（编码唯一，用于创建校验）"""
        async with self.transaction() as session:
            stmt = (
                select(SysRole)
                .options(selectinload(SysRole.permissions))
                .where(SysRole.code == code)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_id(self, role_id: str) -> Optional[SysRole]:
        """按ID查询角色（预加载权限）- 供外部单独查询使用"""
        async with self.transaction() as session:
            stmt = (
                select(SysRole)
                .options(selectinload(SysRole.permissions))
                .where(SysRole.id == role_id)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def list_all(self, offset: int = 0, limit: int = 100) -> List[SysRole]:
        """分页查询角色列表（预加载权限）"""
        async with self.transaction() as session:
            stmt = (
                select(SysRole)
                .options(selectinload(SysRole.permissions))
                .offset(offset)
                .limit(limit)
                .order_by(SysRole.create_time.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def count_total(self) -> int:
        """查询角色总数"""
        async with self.transaction() as session:
            stmt = select(SysRole)
            result = await session.execute(stmt)
            return len(result.scalars().all())

    # ------------------------------
    # 写操作类方法（无修改）
    # ------------------------------
    async def create(self, role_in: RoleCreate, session: AsyncSession) -> SysRole:
        """创建角色（含权限分配，需在事务内执行）"""
        # 1. 创建角色基础记录
        db_role = SysRole(
            name=role_in.name,
            code=role_in.code,
            description=role_in.description,
            is_active=role_in.is_active
        )
        session.add(db_role)
        await session.flush()  # 获取角色ID

        # 2. 分配权限（若有）
        if role_in.permission_ids:
            await self.assign_permissions(db_role.id, role_in.permission_ids, session)

        # 3. 预加载权限并返回
        await session.refresh(db_role, attribute_names=["permissions"])
        # 防止序列化时permissions为None
        if not db_role.permissions:
            db_role.permissions = []
        return db_role

    async def assign_permissions(self, role_id: str, permission_ids: List[str], session: AsyncSession):
        """为角色分配权限（先清空再新增，需在事务内执行）"""
        # 1. 清空现有权限关联
        delete_stmt = delete(sys_role_permission).where(sys_role_permission.c.role_id == role_id)
        await session.execute(delete_stmt)

        # 2. 批量插入新权限关联
        if permission_ids:
            insert_stmt = insert(sys_role_permission).values(
                [{"role_id": role_id, "permission_id": perm_id} for perm_id in permission_ids]
            )
            await session.execute(insert_stmt)

    # ------------------------------
    # 【核心修复】update方法：在当前Session内查询角色，避免实例归属错误
    # ------------------------------
    async def update(self, role_id: str, role_update: RoleUpdate, session: AsyncSession) -> Optional[SysRole]:
        """更新角色信息（含权限更新，需在事务内执行）"""
        # 1. 【修复】在当前Session内查询角色（不再调用self.get_by_id，避免创建新Session）
        stmt = (
            select(SysRole)
            .options(selectinload(SysRole.permissions))  # 预加载权限，确保数据完整
            .where(SysRole.id == role_id)
        )
        result = await session.execute(stmt)
        role = result.scalars().first()  # 该角色实例属于当前Session
        if not role:
            return None  # 不存在返回None

        # 2. 更新基础字段（仅更新非None值）
        update_data = role_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key != "permission_ids":  # 权限单独处理
                setattr(role, key, value)

        # 3. 更新权限（若有）
        if "permission_ids" in update_data:
            await self.assign_permissions(role_id, update_data["permission_ids"], session)

        # 4. 刷新数据并返回（当前Session内操作，无归属问题）
        await session.refresh(role, attribute_names=["permissions"])
        return role

    async def delete(self, role_id: str, session: AsyncSession) -> bool:
        """删除角色（需在事务内执行）- 后续可参考update方法优化查询逻辑"""
        # 【可选优化】后续可改为在当前Session内查询，避免Session混用
        role = await self.get_by_id(role_id)
        if not role:
            return False
        # 注意：若按update方法优化查询，需确保role属于当前Session
        await session.delete(role)
        return True

    async def get_options(self) -> List[SysRole]:
        """
        获取角色选项（启用状态且未删除的角色）

        返回：
        - 角色列表，包含 id, name, code 字段
        """
        print("🔵 ===== RoleRepository.get_options 被调用 =====")

        try:
            # async with self.async_db_session() as session:
            async with self.transaction() as session:
                # 构建查询：状态为启用(1)且未删除(0)的角色
                stmt = (
                    select(SysRole)
                    .where(
                        SysRole.status == 1,  # 启用状态
                        SysRole.is_deleted == 0  # 未删除
                    )
                    .order_by(SysRole.sort, SysRole.create_time.desc())  # 按排序和创建时间排序
                )

                result = await session.execute(stmt)
                roles = result.scalars().all()

                print(f"✅ 从数据库获取角色选项: 共 {len(roles)} 个角色")
                for role in roles:
                    print(f"   - {role.name} ({role.code}): ID={role.id}")

                return roles

        except Exception as e:
            print(f"❌ 查询角色选项失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise