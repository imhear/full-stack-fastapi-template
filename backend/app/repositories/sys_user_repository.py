"""
用户模块数据访问层
backend/app/db/repositories/user_repository.py
上次更新：2025/12/1
"""
from app.core.exceptions import BadRequest, ResourceNotFound

"""
用户模块数据访问层 - 重构版（使用查询构建器）
"""
from sqlmodel import select, delete, insert
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from contextlib import asynccontextmanager
from typing import Optional, List, AsyncGenerator, Tuple, Dict, Any
from datetime import datetime

from app.models import SysUser, sys_user_role, SysRole
from app.schemas.sys_user import UserCreateWithHash
from sqlalchemy import select as sql_select, func, or_
from sqlalchemy.orm import selectinload

# 导入查询构建器
from app.core.query_builder import create_user_query_builder


class UserRepository:
    """
    标准Repo层实现（使用查询构建器）：
    1. 注入会话工厂，自主创建事务会话
    2. 事务上下文统一管理会话生命周期
    3. 使用查询构建器实现灵活的查询条件
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

    async def get_user_form_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户表单数据（用于前端编辑）

        Args:
            user_id: 用户ID

        Returns:
            包含用户表单数据的字典，包括：
            - id: 用户ID
            - username: 用户名
            - nickname: 昵称
            - gender: 性别
            - mobile: 手机号
            - avatar: 头像
            - email: 邮箱
            - status: 状态
            - deptId: 部门ID
            - roleIds: 角色ID列表
            - openId: 微信openid
        """
        async with self.transaction() as session:
            # 查询用户并预加载角色关系
            stmt = (
                select(SysUser)
                .options(selectinload(SysUser.roles))
                .where(
                    SysUser.id == user_id,
                    SysUser.is_deleted == 0
                )
            )

            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # 提取角色ID列表
            role_ids = []
            if hasattr(user, 'roles') and user.roles:
                for role in user.roles:
                    if hasattr(role, 'id'):
                        role_ids.append(str(role.id))

            # 构建表单数据
            form_data = {
                'id': str(user.id) if user.id else None,
                'username': user.username,
                'nickname': user.nickname or user.username,
                'gender': user.gender,
                'mobile': user.mobile,
                'avatar': user.avatar,
                'email': user.email,
                'status': user.status,
                'deptId': str(user.dept_id) if user.dept_id else None,
                'roleIds': role_ids,
                'openId': user.openid  # 注意：数据库字段是openid，这里需要转换为openId
            }

            # 清理None值
            return {k: v for k, v in form_data.items() if v is not None}


    # ------------------------------
    # 查询类方法（使用查询构建器重构）
    # ------------------------------
    async def get_by_id(self, user_id: str) -> Optional[SysUser]:
        """按ID查询用户（深度预加载）"""
        async with self.transaction() as session:
            stmt = (
                select(SysUser)
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
                .where(SysUser.id == user_id)
            )
            result = await session.execute(stmt)
            if not result:
                raise ResourceNotFound(detail=f"用户ID '{user_id}' 不存在")
            return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[SysUser]:
        """按用户名查询用户（深度预加载）"""
        async with self.transaction() as session:
            stmt = (
                select(SysUser)
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
                .where(SysUser.username == username)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[SysUser]:
        """按邮箱查询用户（深度预加载）"""
        async with self.transaction() as session:
            stmt = (
                select(SysUser)
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
                .where(SysUser.email == email)
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def list_all(
            self,
            offset: int = 0,
            limit: int = 100,
            **filters  # 接收任意过滤参数
    ) -> List[SysUser]:
        """
        分页查询用户列表（使用查询构建器）

        Args:
            offset: 偏移量
            limit: 每页数量
            **filters: 过滤条件，支持：
                - status: 状态过滤
                - username__like: 用户名模糊搜索
                - nickname__like: 昵称模糊搜索
                - keywords: 多字段关键词搜索
                - create_time_range: 创建时间范围
                - status__in: 状态IN查询
        """
        async with self.transaction() as session:
            # 创建基础查询
            base_query = (
                select(SysUser)
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
            )

            # 使用查询构建器
            query_builder = create_user_query_builder()

            # 添加过滤条件
            query_builder.filter(**filters)

            # 构建分页查询
            query = query_builder.paginate(offset=offset, limit=limit).build_paginated(base_query)

            result = await session.execute(query)
            return result.scalars().all()

    async def list_all_with_count(
            self,
            offset: int = 0,
            limit: int = 100,
            **filters
    ) -> Tuple[List[SysUser], int]:
        """
        一次查询返回数据和总数（使用窗口函数）

        Args:
            offset: 偏移量
            limit: 每页数量
            **filters: 支持多种过滤条件，支持排序参数：
                - status: 状态过滤
                - username__like: 用户名模糊搜索
                - nickname__like: 昵称模糊搜索
                - keywords: 多字段关键词搜索
                - create_time_range: 创建时间范围
                - status__in: 状态IN查询
                - sort_field: 排序字段
                - sort_direction: 排序方向（ASC/DESC）

        Returns:
            (用户列表, 总数)
        """
        async with self.transaction() as session:
            # 使用窗口函数同时获取数据和总数
            stmt = (
                select(
                    SysUser,
                    func.count(SysUser.id).over().label('total_count')
                )
                .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
            )

            # 使用查询构建器
            query_builder = create_user_query_builder()
            query_builder.filter(**filters)

            # 提取排序参数
            sort_field = filters.get('sort_field')
            sort_direction = filters.get('sort_direction', 'DESC')

            # 应用排序
            if sort_field:
                # 获取字段对象
                field_mapping = {
                    'create_time': SysUser.create_time,
                    'update_time': SysUser.update_time,
                    'username': SysUser.username,
                    'nickname': SysUser.nickname,
                    'gender': SysUser.gender,
                    'status': SysUser.status,
                    'mobile': SysUser.mobile,
                    'email': SysUser.email,
                    'dept_id': SysUser.dept_id
                }

                field_obj = field_mapping.get(sort_field)
                if field_obj:
                    if sort_direction.upper() == 'ASC':
                        query_builder.order_by(field_obj.asc())
                    else:
                        query_builder.order_by(field_obj.desc())

            # 使用 build_paginated 应用过滤、排序和分页
            query = query_builder.paginate(offset=offset, limit=limit).build_paginated(stmt)

            print(f"📨 query数据: {query}")

            # 执行查询
            result = await session.execute(query)
            rows = result.all()

            if not rows:
                return [], 0

            # 提取数据和总数
            users = [row[0] for row in rows]
            total = rows[0].total_count if rows[0].total_count else 0

            return users, total

    async def list_all_by_ids(
            self,
            user_ids: List[str],
            session: AsyncSession,
            include_deleted: bool = False
    ) -> List[SysUser]:
        """
        根据ID列表批量查询用户

        Args:
            user_ids: 用户ID列表
            session: 数据库会话
            include_deleted: 是否包含已删除的用户（默认不包含）

        Returns:
            用户对象列表
        """
        if not user_ids:
            return []

        # 构建查询
        stmt = (
            select(SysUser)
            .where(SysUser.id.in_(user_ids))
        )

        # 如果不包含已删除的用户，添加过滤条件
        if not include_deleted:
            stmt = stmt.where(SysUser.is_deleted == 0)

        result = await session.execute(stmt)
        users = result.scalars().all()

        # 创建ID到用户的映射，保持输入ID的顺序
        user_map = {str(user.id): user for user in users}

        # 按原始ID顺序返回用户列表
        ordered_users = []
        for user_id in user_ids:
            if user_id in user_map:
                ordered_users.append(user_map[user_id])

        return ordered_users



    # async def list_all_with_count(
    #         self,
    #         offset: int = 0,
    #         limit: int = 100,
    #         **filters
    # ) -> Tuple[List[SysUser], int]:
    #     """
    #     一次查询返回数据和总数（使用窗口函数）
    #
    #     Args:
    #         offset: 偏移量
    #         limit: 每页数量
    #         **filters: 过滤条件
    #
    #     Returns:
    #         (用户列表, 总数)
    #     """
    #     async with self.transaction() as session:
    #         # 使用窗口函数同时获取数据和总数
    #         from sqlalchemy import over
    #
    #         # 创建基础查询（包含窗口函数）
    #         stmt = (
    #             select(
    #                 SysUser,
    #                 func.count(SysUser.id).over().label('total_count')
    #             )
    #             .options(selectinload(SysUser.roles).selectinload(SysRole.permissions))
    #         )
    #
    #         # 使用查询构建器应用过滤条件
    #         query_builder = create_user_query_builder()
    #         query_builder.filter(**filters)
    #
    #         # 构建查询（不包含分页）
    #         query = query_builder.build(stmt)
    #
    #         # 应用分页
    #         query = query.offset(offset).limit(limit)
    #
    #         # 执行查询
    #         result = await session.execute(query)
    #         rows = result.all()
    #
    #         if not rows:
    #             return [], 0
    #
    #         # 提取数据和总数
    #         users = [row[0] for row in rows]
    #         total = rows[0].total_count if rows[0].total_count else 0
    #
    #         return users, total

    async def count_total(self, **filters) -> int:
        """
        统计符合条件的用户总数

        Args:
            **filters: 过滤条件
        """
        async with self.transaction() as session:
            stmt = select(func.count(SysUser.id))

            # 使用查询构建器应用过滤条件
            query_builder = create_user_query_builder()
            query_builder.filter(**filters)
            query = query_builder.build(stmt)

            result = await session.execute(query)
            count = result.scalar() or 0
            return count

    # ------------------------------
    # 其他方法保持不变
    # ------------------------------
    async def check_role_in_use(self, role_id: str) -> bool:
        """检查角色是否被用户使用"""
        async with self.transaction() as session:
            stmt = select(sys_user_role.c.user_id).where(sys_user_role.c.role_id == role_id).limit(1)
            result = await session.execute(stmt)
            return result.scalars().first() is not None

    async def create(self, user_in: UserCreateWithHash, session: AsyncSession) -> SysUser:
        """创建用户"""

        try:
            # 创建用户对象
            db_user = SysUser(
                username=user_in.username,
                nickname=user_in.nickname,
                gender=user_in.gender,
                password=user_in.hashed_password,  # 存储加密后的密码
                dept_id=user_in.dept_id,
                mobile=user_in.mobile,
                status=user_in.status,
                email=user_in.email
            )

            session.add(db_user)
            await session.flush()  # 获取生成的ID

            # 分配角色（如果有）
            if user_in.role_ids:
                await self.assign_roles(db_user.id, user_in.role_ids, session)

            # 刷新获取完整数据
            await session.refresh(db_user, attribute_names=["roles"])

            return db_user

        except Exception as e:
            # print(f"❌ 仓库层创建用户失败: {str(e)}")
            # print(f"❌ 异常类型: {type(e)}")
            #
            # # 打印更详细的异常信息
            # import traceback
            # traceback.print_exc()

            # 如果是唯一性约束冲突
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                if "username" in str(e):
                    raise BadRequest(detail=f"用户名 '{user_in.username}' 已存在")
                elif "email" in str(e):
                    raise BadRequest(detail=f"邮箱 '{user_in.email}' 已被注册")
            raise

    async def update(self, user: SysUser, session: AsyncSession) -> SysUser:
        """更新用户信息"""
        session.add(user)
        await session.refresh(user, attribute_names=["roles"])
        return user

    async def clear_roles(self, user_id: str, session: AsyncSession):
        """清空用户所有角色"""
        stmt = delete(sys_user_role).where(sys_user_role.c.user_id == user_id)
        await session.execute(stmt)

    async def assign_roles(self, user_id: str, role_ids: List[str], session: AsyncSession):
        """为用户分配角色"""
        await self.clear_roles(user_id, session)
        if role_ids:
            stmt = insert(sys_user_role).values(
                [{"user_id": user_id, "role_id": rid} for rid in role_ids]
            )
            await session.execute(stmt)

    async def delete(self, user_id: str, session: AsyncSession) -> bool:
        """删除用户"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await session.delete(user)
        return True