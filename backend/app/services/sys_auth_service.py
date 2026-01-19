# app/services/auth_service.py
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.security import verify_password
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from app.core.security import decode_jwt_token
from app.repositories.sys_user_repository import UserRepository
from app.models import SysUser
from app.schemas.sys_user import TokenPayload


class AuthService:
    """认证Service层：处理用户登录、Token校验"""
    def __init__(self, user_repository: UserRepository, async_db_session: AsyncSession):
        self.user_repository = user_repository
        self.async_db_session = async_db_session

    # ------------------------------
    # 核心业务：用户认证（登录）
    # ------------------------------
    async def authenticate_user(self, email: str, password: str) -> Optional[SysUser]:
        """
        认证用户：
        1. 按邮箱查询用户
        2. 校验密码
        3. 校验用户是否激活
        4. 认证成功返回用户，失败返回None
        """
        # 1. 查询用户
        user = await self.user_repository.get_by_email(email=email)
        if not user:
            return None  # 邮箱不存在

        # 2. 校验密码（调用core.security的verify_password）
        if not verify_password(plain_password=password, hashed_password=user.hashed_password):
            return None  # 密码错误

        # 3. 校验用户是否激活
        if not user.is_active:
            return None  # 用户未激活

        return user

    # ------------------------------
    # 核心业务：Token解析获取当前用户
    # ------------------------------
    async def get_current_user(self, token: str) -> SysUser:
        """
        从Token获取当前用户：
        1. 解析Token
        2. 按用户ID查询用户
        3. 校验用户是否激活
        """
        try:
            # 1. 解析Token（调用core.security的decode_jwt_token）
            payload = decode_jwt_token(token)
            token_data = TokenPayload(** payload)
        except (InvalidTokenError, ValidationError) as e:
            # Token无效或格式错误
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Could not validate credentials: {str(e).split(chr(10))[0]}"
            )

        # 2. 查询用户
        user = await self.user_repository.get_by_id(user_id=token_data.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{token_data.sub}' not found"
            )

        # 3. 校验用户激活状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user, cannot access resources"
            )

        return user