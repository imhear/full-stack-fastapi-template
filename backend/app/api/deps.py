"""
API 依赖项配置文件
backend/app/api/deps.py
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from dependency_injector.wiring import inject, Provide
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session
from collections.abc import Generator

from app.di.container import Container
from app.services.captcha_service import CaptchaService
from app.services.sys_auth_service import AuthService
from app.core.security import reusable_oauth2
from app.models import SysUser
from fastapi import HTTPException, status

from app.services.sys_dept_service import DeptService
from app.services.sys_role_service import RoleService
from app.services.sys_user_service import UserService
from app.services.sys_dict_service import DictService

import redis.asyncio as redis
print(f"🔍 DEBUG: 导入依赖注入模块")
# ------------------------------
# 核心：异步DB会话依赖（无self问题）
# ------------------------------
@inject
async def get_async_db(
    session: AsyncSession = Depends(Provide[Container.async_db])
) -> AsyncSession:
    """注入异步会话，无需额外配置（由容器统一管理）"""
    yield session


# ------------------------------
# 同步DB会话依赖（核心修正）
# ------------------------------
@inject
def get_sync_db(
    session: Session = Depends(Provide[Container.sync_db])
) -> Generator[Session, None, None]:
    """
    通过DI容器注入同步会话，与异步会话保持一致的注入方式。
    不再直接导入引擎，而是直接使用容器提供的会话。
    """
    yield session


# ------------------------------
# 认证依赖：获取当前用户（OAuth2）
# ------------------------------
@inject
async def get_current_user(
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
    token: str = Depends(reusable_oauth2)
) -> SysUser:
    """从Token中解析用户，验证有效性"""
    user = await auth_service.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user


# ------------------------------
# 超级用户依赖（权限控制）
# ------------------------------
async def get_current_active_superuser(
    current_user: SysUser = Depends(get_current_user)
) -> SysUser:
    """仅允许超级用户访问"""
    # TODO 临时注释
    # if not current_user.is_superuser:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough privileges (requires superuser)"
    #     )
    return current_user


# ------------------------------
# 类型别名（简化API层代码）
# ------------------------------
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_db)]
SyncSessionDep = Annotated[Session, Depends(get_sync_db)]
CurrentUser = Annotated[SysUser, Depends(get_current_user)]
CurrentSuperuser = Annotated[SysUser, Depends(get_current_active_superuser)]

# 依赖类型注解（简化写法）
AuthServiceDep = Annotated[AuthService, Depends(Provide[Container.auth_service])]
UserServiceDep = Annotated[UserService, Depends(Provide[Container.user_service])]
RoleServiceDep = Annotated[RoleService, Depends(Provide[Container.role_service])]
DeptServiceDep = Annotated[DeptService, Depends(Provide[Container.dept_service])]
DictServiceDep = Annotated[DictService, Depends(Provide[Container.dict_service])]

print(f"🔍 DEBUG: 导入 DeptServiceDep")
OAuth2FormDep = Annotated[OAuth2PasswordRequestForm, Depends()]

CaptchaServiceDep = Annotated[CaptchaService, Depends(Provide[Container.captcha_service])]