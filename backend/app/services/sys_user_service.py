"""
用户模块业务层
backend/app/services/user_service.py
上次更新：2025/12/1
"""
from typing import Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import SysUser
from app.repositories.sys_user_repository import UserRepository
from app.schemas.sys_user import UserCreate, UserCreateWithHash, Message, UserUpdate, UserList, UserUpdateSelfPassword
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import ResourceNotFound, BadRequest
from app.services.redis_service import RedisService  # 新增：RedisService依赖


class UserService:
    """用户Service层：仅管业务逻辑，不碰事务/DB操作"""
    def __init__(self, user_repository: UserRepository,
                 async_db_session: AsyncSession,
                 redis_service: RedisService):  # 新增：RedisService依赖
        self.user_repository = user_repository  # 注入Repo（无状态）
        self.async_db_session = async_db_session  # 注入请求级会话（备用，Repo主要用自己的事务）
        self.redis_service = redis_service  # 新增：RedisService实例

    # ------------------------------
    # 核心业务：创建用户
    # ------------------------------
    async def create_user(self, user_in: UserCreate) -> SysUser:
        """创建用户（业务校验+调用Repo）"""
        # 1. 业务校验1：邮箱唯一性
        existing_user = await self.user_repository.get_by_email(email=user_in.email)
        if existing_user:
            raise BadRequest(detail=f"Email '{user_in.email}' already exists")

        # 2. 业务校验2：密码长度（前端可能也有校验，后端二次确保）
        if len(user_in.password) < 6:
            raise BadRequest(detail="Password must be at least 6 characters")

        # 3. 业务逻辑：密码加密（Service层负责，Repo不碰密码逻辑）
        user_in_with_hash = UserCreateWithHash(
            **user_in.model_dump(exclude={"password"}),
            hashed_password=get_password_hash(user_in.password),
            is_active=True  # 默认创建激活用户
        )

        # 4. 调用Repo创建（进入Repo事务上下文）
        async with self.user_repository.transaction() as session:
            return await self.user_repository.create(
                user_in=user_in_with_hash,
                session=session  # 传递Repo事务内的会话
            )

    # ------------------------------
    # 扩展业务：创建用户并分配角色
    # ------------------------------
    async def create_user_with_roles(self, user_in: UserCreate, role_ids: List[str]) -> SysUser:
        """创建用户+分配角色（原子操作，失败则回滚）"""
        # 1. 先创建用户（复用已有逻辑）
        async with self.user_repository.transaction() as session:
            # 嵌套事务：创建用户+分配角色，确保原子性
            try:
                # 创建用户
                user = await self.create_user(user_in)
                # 分配角色（调用Repo的assign_roles，需在同一事务内）
                await self.user_repository.assign_roles(
                    user_id=user.id,
                    role_ids=role_ids,
                    session=session
                )
                # 刷新用户数据（包含最新角色）
                return await self.user_repository.get_by_id(user_id=user.id)
            except IntegrityError as e:
                # 捕获数据库完整性错误（如角色ID不存在）
                raise BadRequest(detail=f"Assign roles failed: {str(e).split(chr(10))[0]}")  # 截取关键错误信息

    # ------------------------------
    # 基础业务：查询用户
    # ------------------------------
    async def get_user_by_id(self, user_id: str) -> SysUser:
        """按ID查询用户（不存在则抛异常）"""
        user = await self.user_repository.get_by_id(user_id=user_id)
        if not user:
            raise ResourceNotFound(detail=f"User with ID '{user_id}' not found")
        return user

    async def get_user_by_email(self, email: str) -> Optional[SysUser]:
        """按邮箱查询用户（不存在返回None）"""
        return await self.user_repository.get_by_email(email=email)

    async def list_users(self, offset: int = 0, limit: int = 100) -> UserList:
        """分页查询用户列表（返回总数+列表）"""
        users = await self.user_repository.list_all(offset=offset, limit=limit)
        total = await self.user_repository.count_total()
        return UserList(items=users, total=total)

    # ------------------------------
    # 基础业务：更新用户
    # ------------------------------
    async def update_last_login(self, user_id: str) -> None:
        """更新用户最后登录时间（登录成功后调用）"""
        async with self.user_repository.transaction() as session:
            # 1. 业务校验：用户存在且激活
            user = await self.user_repository.get_by_id(user_id=user_id)
            if not user:
                raise ResourceNotFound(detail=f"User '{user_id}' not found")
            if not user.is_active:
                raise BadRequest(detail=f"User '{user_id}' is inactive, cannot update last login")

            # 2. 调用Repo更新
            user.last_login = datetime.now(ZoneInfo("UTC"))  # 统一UTC时间
            await self.user_repository.update(user=user, session=session)

    async def update_password(self, user_id: str, new_password: str) -> Message:
        """更新用户密码（需校验用户状态）"""
        # 1. 业务校验：密码长度
        if len(new_password) < 6:
            raise BadRequest(detail="New password must be at least 6 characters")

        async with self.user_repository.transaction() as session:
            # 2. 业务校验：用户存在且激活
            user = await self.user_repository.get_by_id(user_id=user_id)
            if not user:
                raise ResourceNotFound(detail=f"User '{user_id}' not found")
            if not user.is_active:
                raise BadRequest(detail=f"User '{user_id}' is inactive, cannot update password")

            # 3. 密码加密+更新
            user.hashed_password = get_password_hash(new_password)
            await self.user_repository.update(user=user, session=session)
            return Message(message="Password updated successfully")

    async def update_self_password(self, user_id: str, user_update: UserUpdateSelfPassword) -> Message:
        """修改个人密码（带旧密码校验）"""
        old_password = user_update.password
        new_password = user_update.new_password

        # 1. 业务校验：密码长度
        if len(new_password) < 6:
            raise BadRequest(detail="New password must be at least 6 characters")

        async with self.user_repository.transaction() as session:
            # 2. 业务校验：用户存在且激活
            user = await self.user_repository.get_by_id(user_id=user_id)
            if not user:
                raise ResourceNotFound(detail=f"User '{user_id}' not found")
            if not user.is_active:
                raise BadRequest(detail=f"User '{user_id}' is inactive, cannot update password")

            # 3. 校验密码（调用core.security的verify_password）
            if not verify_password(plain_password=old_password, hashed_password=user.hashed_password):
                # return None  # 密码错误
                return Message(message="密码错误")

            # 4. 密码加密+更新
            user.hashed_password = get_password_hash(new_password)
            await self.user_repository.update(user=user, session=session)
            return Message(message="Password updated successfully")

    async def assign_roles(self, user_id: str, role_ids: List[str]) -> Message:
        """为用户分配角色（先清空再分配）"""
        # 1. 业务校验：用户存在
        user = await self.user_repository.get_by_id(user_id=user_id)
        if not user:
            raise ResourceNotFound(detail=f"User '{user_id}' not found")

        # 2. 调用Repo分配角色
        async with self.user_repository.transaction() as session:
            await self.user_repository.assign_roles(
                user_id=user_id,
                role_ids=role_ids,
                session=session
            )
        return Message(message="Roles assigned successfully to user")

    async def update_user(self, user_id: str, user_update: UserUpdate) -> SysUser:
        """更新用户基础信息（含角色更新）"""
        # 1. 业务校验：用户存在
        user = await self.user_repository.get_by_id(user_id=user_id)
        if not user:
            raise ResourceNotFound(detail=f"User '{user_id}' not found")
        print("----update_user--1--")
        print(user)
        print("----update_user--1--")

        # 2. 业务校验：邮箱唯一性（若更新邮箱）
        if user_update.email and user_update.email != user.email:
            existing_user = await self.user_repository.get_by_email(email=user_update.email)
            if existing_user:
                raise BadRequest(detail=f"Email '{user_update.email}' already exists")

        async with self.user_repository.transaction() as session:
            # 3. 更新基础字段
            update_data = user_update.model_dump(exclude_unset=True)

            print("----update_data--1--")
            print(update_data)
            print("----update_data--1--")

            for key, value in update_data.items():
                if key != "role_ids":  # 角色单独处理
                    setattr(user, key, value)

            print("----update_user--2--")
            print(user)
            print("----update_user--2--")

            # 4. 更新角色（若有）
            if "role_ids" in update_data:
                await self.user_repository.assign_roles(
                    user_id=user_id,
                    role_ids=update_data["role_ids"],
                    session=session
                )

            # 5. 调用Repo更新并返回
            updated_user = await self.user_repository.update(user=user, session=session)
            print("----update_user--2--")
            print(updated_user)
            print("----update_user--2--")

            return updated_user

    # ------------------------------
    # 基础业务：删除用户
    # ------------------------------
    async def delete_user(self, user_id: str) -> Message:
        """删除用户（需校验用户是否存在）"""
        async with self.user_repository.transaction() as session:
            success = await self.user_repository.delete(user_id=user_id, session=session)
            if not success:
                raise ResourceNotFound(detail=f"User '{user_id}' not found")
        return Message(message=f"User '{user_id}' deleted successfully")