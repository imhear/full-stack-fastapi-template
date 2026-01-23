"""
backend/app/services/user_service.py
上次更新：2026/1/21
用户服务层 - 集成字段映射功能

行业最佳实践：
1. 服务层负责业务逻辑和数据结构转换
2. 保持数据库模型纯洁（只存储数据）
3. 统一出口：所有返回前端的数据都经过标准化转换
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import SysUser
from app.repositories.sys_user_repository import UserRepository
from app.schemas.sys_user import (
    UserCreate, UserCreateWithHash, Message, UserUpdate, UserList,
    UserUpdateSelfPassword
)
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import ResourceNotFound, BadRequest
from app.services.redis_service import RedisService
from app.services.mappers.user_mapper import user_mapper


class UserService:
    """
    用户服务 - 增强版（支持字段映射）

    架构原则：
    1. 单一职责：每个方法只做一件事
    2. 明确接口：输入输出类型明确
    3. 错误处理：统一异常处理
    4. 数据转换：统一出口转换
    """

    def __init__(self, user_repository: UserRepository,
                 async_db_session: AsyncSession,
                 redis_service: RedisService):
        self.user_repository = user_repository
        self.async_db_session = async_db_session
        self.redis_service = redis_service

    # ==================== 用户信息查询方法 ====================

    async def get_user_by_id(self, user_id: str) -> SysUser:
        """
        根据ID获取用户（原始数据）

        用于内部业务处理，不直接返回前端

        Args:
            user_id: 用户ID

        Returns:
            SysUser ORM对象

        Raises:
            ResourceNotFound: 用户不存在
        """
        user = await self.user_repository.get_by_id(user_id=user_id)
        if not user:
            raise ResourceNotFound(detail=f"用户ID '{user_id}' 不存在")
        return user

    # async def get_user_info(self, user_id: str) -> Dict[str, Any]:
    #     """
    #     获取用户信息（前端格式）
    #
    #     这是标准接口：返回前端友好的数据结构
    #
    #     Args:
    #         user_id: 用户ID
    #
    #     Returns:
    #         前端格式的用户信息字典
    #     """
    #     user = await self.get_user_by_id(user_id)
    #     return await self._convert_user_to_frontend(user)

    async def get_current_user_info(self, current_user: SysUser) -> Dict[str, Any]:
        """
        获取当前登录用户信息（支持 UserMeResponse 格式）

        使用专门的转换方法转换为 UserMeResponse 格式
        """
        # 如果角色未加载，重新查询完整数据
        if not hasattr(current_user, 'roles') or current_user.roles is None:
            user = await self.user_repository.get_by_id(current_user.id)
        else:
            user = current_user

        return user_mapper.to_user_me_response(user)
        # ==================== 需要清理的垃圾代码 ====================
        # if not hasattr(current_user, 'roles') or current_user.roles is None:
        #     # 重新加载完整用户数据
        #     user = await self.user_repository.get_by_id(current_user.id)
        # else:
        #     user = current_user

        # # 直接构建符合 UserMeResponse 格式的字典
        # user_data = {
        #     "userId": str(user.id),
        #     "username": user.username,
        #     "nickname": user.nickname,
        #     "avatar": user.avatar,
        #     "gender": user.gender,
        #     "mobile": user.mobile,
        #     "email": user.email,
        #     "status": user.status,
        #     "deptId": str(user.dept_id) if user.dept_id else None,
        #     "createTime": user.create_time,
        #     "roles": [],
        #     "perms": []
        # }
        #
        # # 提取角色和权限
        # if user.roles:
        #     role_codes = []
        #     permission_codes = set()
        #
        #     for role in user.roles:
        #         if hasattr(role, 'code'):
        #             role_codes.append(role.code)
        #
        #         if hasattr(role, 'permissions'):
        #             for perm in role.permissions:
        #                 if hasattr(perm, 'code'):
        #                     permission_codes.add(perm.code)
        #
        #     user_data["roles"] = role_codes
        #     user_data["perms"] = list(permission_codes)
        #
        # return user_data

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户个人中心信息（前端格式）

        特殊处理：包含更多个人信息

        Args:
            user_id: 用户ID

        Returns:
            前端格式的个人中心信息
        """
        # 获取用户数据，确保加载部门和角色
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFound(detail=f"用户ID '{user_id}' 不存在")

        return user_mapper.to_user_profile(user)
        # ==================== 需要清理的垃圾代码 ====================
        # user = await self.get_user_by_id(user_id)

        # # 直接构建响应数据，避免复杂转换
        # profile_data = {
        #     "id": str(user.id),
        #     "username": user.username,
        #     "nickname": user.nickname,
        #     "avatar": user.avatar,
        #     "gender": user.gender,
        #     "mobile": user.mobile,
        #     "email": user.email,
        #     "createTime": user.create_time.isoformat() if user.create_time else None,
        # }
        #
        # # 添加部门信息（如果关联已加载）
        # if hasattr(user, 'dept') and user.dept:
        #     profile_data['deptName'] = user.dept.name
        #
        # # 添加角色信息
        # if hasattr(user, 'roles') and user.roles:
        #     role_names = [role.name for role in user.roles if hasattr(role, 'name')]
        #     profile_data['roleNames'] = ', '.join(role_names)
        #
        # return profile_data

    async def list_users_frontend(
            self,
            offset: int = 0,
            limit: int = 100,
            filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户列表（前端格式）

        支持分页和过滤

        Args:
            offset: 偏移量
            limit: 每页数量
            filters: 过滤条件

        Returns:
            前端格式的用户列表
        """
        # 获取原始数据，包含部门和角色
        users = await self.user_repository.list_all(offset=offset, limit=limit)

        # 批量转换
        return user_mapper.to_users_list(users)
        # ==================== 需要清理的垃圾代码 ====================
        # 获取原始数据
        # users = await self.user_repository.list_all(offset=offset, limit=limit)
        #
        # # 批量转换
        # results = []
        # for user in users:
        #     user_data = {
        #         "id": str(user.id),
        #         "username": user.username,
        #         "nickname": user.nickname,
        #         "avatar": user.avatar,
        #         "gender": user.gender,
        #         "mobile": user.mobile,
        #         "email": user.email,
        #         "status": user.status,
        #         "createTime": user.create_time.isoformat() if user.create_time else None,
        #         "roleNames": "",
        #         "deptName": ""
        #     }
        #
        #     # 添加角色名称
        #     if hasattr(user, 'roles') and user.roles:
        #         role_names = [role.name for role in user.roles if hasattr(role, 'name')]
        #         user_data['roleNames'] = ', '.join(role_names)
        #
        #     # 添加部门名称
        #     if hasattr(user, 'dept') and user.dept and hasattr(user.dept, 'name'):
        #         user_data['deptName'] = user.dept.name
        #
        #     results.append(user_data)
        #
        # return results

    async def list_users(self, offset: int = 0, limit: int = 100) -> UserList:
        """
        获取用户列表（原始格式）

        用于内部使用或需要原始数据的场景

        Args:
            offset: 偏移量
            limit: 每页数量

        Returns:
            UserList 对象
        """
        users = await self.user_repository.list_all(offset=offset, limit=limit)
        total = await self.user_repository.count_total()
        return UserList(items=users, total=total)

    # ==================== 用户管理方法 ====================

    async def create_user(self, user_in: UserCreate) -> Dict[str, Any]:
        """
        创建用户（返回前端格式）

        Args:
            user_in: 用户创建数据

        Returns:
            前端格式的新用户信息
        """
        # 1. 验证邮箱唯一性
        existing_user = await self.user_repository.get_by_username(username=user_in.username)
        if existing_user:
            raise BadRequest(detail=f"邮箱 '{user_in.email}' 已被注册")

        # 2. 密码验证
        if len(user_in.password) < 6:
            raise BadRequest(detail="密码长度至少6位")

        # 3. 状态映射
        is_active = True
        if hasattr(user_in, 'status') and user_in.status is not None:
            is_active = user_in.status == 1

        # 4. 创建用户数据
        user_in_with_hash = UserCreateWithHash(
            **user_in.model_dump(exclude={"password"}),
            hashed_password=get_password_hash(user_in.password),
            is_active=is_active
        )

        # 5. 调用仓库层创建
        async with self.user_repository.transaction() as session:
            user = await self.user_repository.create(
                user_in=user_in_with_hash,
                session=session
            )

        # 6. 转换为前端格式返回
        return user_mapper.to_user_detail(user)
        # ==================== 需要清理的垃圾代码 ====================
        # return await self._convert_user_to_frontend(user)

    async def update_user(self, user_id: str, user_update: UserUpdate) -> Dict[str, Any]:
        """
        更新用户信息（返回前端格式）

        Args:
            user_id: 用户ID
            user_update: 更新数据

        Returns:
            前端格式的更新后用户信息
        """
        # 1. 获取用户
        user = await self.get_user_by_id(user_id)

        # TODO 待实现邮箱字段
        # 2. 邮箱唯一性验证（如果修改邮箱）
        # if user_update.email and user_update.email != user.email:
        #     existing_user = await self.user_repository.get_by_email(email=user_update.email)
        #     if existing_user:
        #         raise BadRequest(detail=f"邮箱 '{user_update.email}' 已被使用")

        async with self.user_repository.transaction() as session:
            # 3. 提取更新数据
            update_data = user_update.model_dump(exclude_unset=True)

            # 4. 处理状态映射
            if "status" in update_data:
                user.is_active = update_data["status"] == 1

            # 5. 更新基础字段
            for key, value in update_data.items():
                if key not in ["role_ids", "status"]:
                    setattr(user, key, value)

            # 6. 更新角色（如果有）
            if "role_ids" in update_data:
                await self.user_repository.assign_roles(
                    user_id=user_id,
                    role_ids=update_data["role_ids"],
                    session=session
                )

            # 7. 保存更新
            await self.user_repository.update(user=user, session=session)

            # 8. 重新加载完整数据
            updated_user = self.get_user_by_id(user_id)

            # 9. 转换为前端格式返回
        return user_mapper.to_user_detail(updated_user)
            # ==================== 需要清理的垃圾代码 ====================
            # 7. 保存更新
            # updated_user = await self.user_repository.update(user=user, session=session)

        # 8. 转换为前端格式返回
        # return await self._convert_user_to_frontend(updated_user)

    async def update_last_login(self, user_id: str) -> None:
        """
        更新最后登录时间

        Args:
            user_id: 用户ID
        """
        # TODO 待实现最后登录字段逻辑+同步修改数据模型、校验模型、usermapper类
        pass
        # async with self.user_repository.transaction() as session:
        #     user = await self.user_repository.get_by_id(user_id=user_id)
        #     if not user:
        #         raise ResourceNotFound(detail=f"用户 '{user_id}' 不存在")
        #
        #     user.last_login = datetime.utcnow()
        #     await self.user_repository.update(user=user, session=session)

    async def update_password(self, user_id: str, new_password: str) -> Message:
        """
        重置用户密码

        Args:
            user_id: 用户ID
            new_password: 新密码

        Returns:
            操作结果消息
        """
        if len(new_password) < 6:
            raise BadRequest(detail="新密码长度至少6位")

        async with self.user_repository.transaction() as session:
            user = await self.user_repository.get_by_id(user_id=user_id)
            if not user:
                raise ResourceNotFound(detail=f"用户 '{user_id}' 不存在")

            user.hashed_password = get_password_hash(new_password)
            await self.user_repository.update(user=user, session=session)

            # 记录密码修改日志（生产环境建议）
            # await self._log_password_change(user_id)

            return Message(message="密码重置成功")

    async def delete_user(self, user_id: str) -> Message:
        """
        删除用户

        Args:
            user_id: 用户ID

        Returns:
            操作结果消息
        """
        async with self.user_repository.transaction() as session:
            success = await self.user_repository.delete(user_id=user_id, session=session)
            if not success:
                raise ResourceNotFound(detail=f"用户 '{user_id}' 不存在")

            # 记录删除日志（生产环境建议）
            # await self._log_user_deletion(user_id)

            return Message(message=f"用户 '{user_id}' 删除成功")

    # ==================== 辅助方法 ====================

    # ==================== 需要清理的垃圾代码 ====================
    # async def _build_user_response(self, user: SysUser) -> Dict[str, Any]:
    #     """
    #     构建通用的用户响应数据
    #
    #     用于需要返回用户信息的场景，如创建、更新用户
    #     """
    #     response_data = {
    #         "id": str(user.id),
    #         "username": user.username,
    #         "nickname": user.nickname,
    #         "avatar": user.avatar,
    #         "gender": user.gender,
    #         "mobile": user.mobile,
    #         "email": user.email,
    #         "status": user.status,
    #         "createTime": user.create_time.isoformat() if user.create_time else None,
    #     }
    #
    #     # 添加角色信息（如果已加载）
    #     if hasattr(user, 'roles') and user.roles:
    #         role_codes = [role.code for role in user.roles if hasattr(role, 'code')]
    #         response_data["roles"] = role_codes
    #
    #         # 提取权限
    #         permission_codes = set()
    #         for role in user.roles:
    #             if hasattr(role, 'permissions'):
    #                 for perm in role.permissions:
    #                     if hasattr(perm, 'code'):
    #                         permission_codes.add(perm.code)
    #         response_data["perms"] = list(permission_codes)
    #
    #     return response_data


    # async def _user_to_dict(self, user: SysUser) -> Dict[str, Any]:
    #     """
    #     将ORM用户对象转换为字典
    #
    #     提取所有需要的字段，便于后续转换
    #
    #     Args:
    #         user: SysUser ORM对象
    #
    #     Returns:
    #         用户数据字典
    #     """
    #     # 基础字段
    #     user_dict = {
    #         'id': user.id,
    #         'username': user.username,
    #         'nickname': user.nickname,
    #         'avatar': user.avatar,
    #         'gender': user.gender,
    #         'mobile': user.mobile,
    #         'status': user.status,
    #         'email': user.email,
    #         'dept_id': user.dept_id,
    #         'create_time': user.create_time,
    #         'create_by': user.create_by,
    #         'update_time': user.update_time,
    #         'update_by': user.update_by,
    #         'roles': user.roles or [],
    #     }
    #
    #     # 提取角色和权限
    #     if user.roles:
    #         role_codes = []
    #         permission_codes = set()
    #
    #         for role in user.roles:
    #             if hasattr(role, 'code'):
    #                 role_codes.append(role.code)
    #
    #             # 提取权限
    #             if hasattr(role, 'permissions'):
    #                 for perm in role.permissions:
    #                     if hasattr(perm, 'code'):
    #                         permission_codes.add(perm.code)
    #
    #         user_dict['role_codes'] = role_codes
    #         user_dict['permission_codes'] = list(permission_codes)
    #     else:
    #         user_dict['role_codes'] = []
    #         user_dict['permission_codes'] = []
    #
    #     return user_dict
    #
    # async def _convert_user_to_frontend(self, user: SysUser) -> Dict[str, Any]:
    #     """
    #     转换用户数据为前端格式（统一出口）
    #
    #     所有返回前端的数据都经过此方法处理
    #
    #     Args:
    #         user: SysUser ORM对象
    #
    #     Returns:
    #         前端格式的用户数据
    #     """
    #     # 转换为字典
    #     print("========转换为字典==========")
    #     user_dict = await self._user_to_dict(user)
    #
    #     # 应用字段映射
    #     print("========应用字段映射==========")
    #     return user_mapper.convert_user_to_frontend(user_dict)
    #
    # async def _convert_frontend_to_backend(self, frontend_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     转换前端数据为后端格式（统一入口）
    #
    #     所有接收的前端数据都经过此方法处理
    #
    #     Args:
    #         frontend_data: 前端数据
    #
    #     Returns:
    #         后端格式的数据
    #     """
    #     return user_mapper.convert_frontend_to_backend(frontend_data)