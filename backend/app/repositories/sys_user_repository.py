"""
用户模块数据访问层
backend/app/db/repositories/user_repository.py
上次更新：2025/12/1
"""
from sqlmodel import select, delete, insert
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload  # selectinload用于预加载
from contextlib import asynccontextmanager
from typing import Optional, List, AsyncGenerator

from app.models import SysUser, sys_user_roles, SysRole  # 【新增】导入Role模型，用于深度预加载
from app.schemas.sys_user import UserCreateWithHash


class UserRepository:
    """
    标准Repo层实现：
    1. 注入会话工厂，自主创建事务会话
    2. 事务上下文统一管理会话生命周期（创建→提交/回滚→关闭）
    3. 纯DB操作，无业务逻辑
    """
    # 注入会话工厂（从DI容器获取）
    def __init__(self, async_session_factory: sessionmaker):
        self.async_session_factory = async_session_factory  # 会话工厂（单例）

    # ------------------------------
    # 核心：标准异步事务上下文（最佳实践2核心）
    # ------------------------------
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self.async_session_factory()  # 新建会话
        try:
            await session.begin()  # 开启事务
            yield session  # 传递会话给Service
            await session.commit()  # 无异常则提交
        except Exception as e:
            await session.rollback()  # 异常则回滚
            raise e  # 抛出异常给Service处理（业务层统一捕获）
        finally:
            await session.close()  # 强制关闭会话，无残留

    # ------------------------------
    # 查询类方法（【核心修复】添加深度预加载：User.roles → Role.permissions）
    # ------------------------------
    async def get_by_email(self, email: str) -> Optional[SysUser]:
        """按邮箱查询用户（深度预加载：角色+角色的权限）"""
        async with self.transaction() as session:
            stmt = (
                select(SysUser)
                # 【修复】深度预加载：先加载User.roles，再加载每个Role的permissions
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
                .where(SysUser.email == email)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[SysUser]:
        """按ID查询用户（深度预加载：角色+角色的权限）"""
        async with self.transaction() as session:
            stmt = (
                select(SysUser)
                # 【修复】深度预加载
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
                .where(SysUser.id == user_id)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def list_all(self, offset: int = 0, limit: int = 100) -> List[SysUser]:
        """分页查询用户列表（深度预加载：角色+角色的权限）"""
        async with self.transaction() as session:
            stmt = (
                select(SysUser)
                # 【修复】深度预加载（关键修改，解决列表查询报错）
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
                .offset(offset)
                .limit(limit)
                .order_by(SysUser.created_at.desc())  # 按创建时间倒序
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def count_total(self) -> int:
        """查询用户总数（无需预加载，仅计数）"""
        async with self.transaction() as session:
            stmt = select(SysUser)
            result = await session.execute(stmt)
            return len(result.scalars().all())

    async def check_role_in_use(self, role_id: str) -> bool:
        """检查角色是否被用户使用（用于角色删除校验）"""
        async with self.transaction() as session:
            stmt = select(sys_user_roles.c.user_id).where(sys_user_roles.c.role_id == role_id).limit(1)
            result = await session.execute(stmt)
            return result.scalars().first() is not None  # 有数据则返回True

    # ------------------------------
    # 写操作类方法（无修改，保持原逻辑）
    # ------------------------------
    async def create(self, user_in: UserCreateWithHash, session: AsyncSession) -> SysUser:
        """创建用户（含角色分配，需在事务内执行）"""
        # 1. 创建用户基础记录
        db_user = SysUser(
            username=user_in.username,
            email=user_in.email,
            hashed_password=user_in.hashed_password,
            full_name=user_in.full_name,
            is_active=user_in.is_active
        )
        session.add(db_user)
        await session.flush()  # 刷新获取用户ID（不提交事务）

        # 2. 分配角色（若有）
        if user_in.role_ids:
            await self.assign_roles(db_user.id, user_in.role_ids, session)

        # 3. 【修复】深度刷新：确保返回的用户包含角色和权限
        await session.refresh(
            db_user,
            attribute_names=["roles"]  # 刷新roles，已通过预加载包含permissions
        )
        return db_user

    async def update(self, user: SysUser, session: AsyncSession) -> SysUser:
        """更新用户信息（需在事务内执行）"""
        session.add(user)
        # 【修复】深度刷新：确保更新后的数据包含角色和权限
        await session.refresh(
            user,
            attribute_names=["roles"]  # 刷新roles，已包含permissions
        )
        return user

    async def clear_roles(self, user_id: str, session: AsyncSession):
        """清空用户所有角色（需在事务内执行）"""
        stmt = delete(sys_user_roles).where(sys_user_roles.c.user_id == user_id)
        await session.execute(stmt)

    async def assign_roles(self, user_id: str, role_ids: List[str], session: AsyncSession):
        """为用户分配角色（先清空再新增，需在事务内执行）"""
        await self.clear_roles(user_id, session)  # 先清空现有角色
        if role_ids:
            # 批量插入角色关联
            stmt = insert(sys_user_roles).values(
                [{"user_id": user_id, "role_id": rid} for rid in role_ids]
            )
            await session.execute(stmt)

    async def delete(self, user_id: str, session: AsyncSession) -> bool:
        """删除用户（需在事务内执行）"""
        user = await self.get_by_id(user_id)  # 先查询用户是否存在
        if not user:
            return False  # 不存在返回False
        await session.delete(user)  # 存在则删除
        return True  # 删除成功返回True