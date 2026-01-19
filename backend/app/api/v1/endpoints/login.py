"""
登录接口文件
backend/app/api/v1/endpoints/login.py
上次更新：2026/1/19
"""
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from dependency_injector.wiring import inject, Provide

from app.di.container import Container
from app.services.sys_auth_service import AuthService
from app.services.sys_user_service import UserService
from app.core import security
from app.core.config import settings
from app.schemas.sys_user import Message, NewPassword, Token, UserOut  # 注意：原UserPublic可能是旧Schema，替换为UserOut
from app.utils.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)
from app.api.deps import CurrentUser, get_current_active_superuser, OAuth2FormDep, AuthServiceDep, UserServiceDep

router = APIRouter(tags=["login"])

# 依赖类型注解（简化写法）
# AuthServiceDep = Annotated[AuthService, Depends(Provide[Container.auth_service])]
# UserServiceDep = Annotated[UserService, Depends(Provide[Container.user_service])]
# OAuth2FormDep = Annotated[OAuth2PasswordRequestForm, Depends()]


# 关键1：接口方法改为async def，支持await调用
@router.post("/login/access-token")
@inject
async def login_access_token(  # 改def→async def
    form_data: OAuth2FormDep,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep
) -> Token:
    """OAuth2 token登录（异步实现）"""
    # 关键2：调用异步AuthService方法时加await
    print("关键2：调用异步AuthService方法时加await")
    user = await auth_service.authenticate_user(
        email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # 关键3：若user_service.update_last_login是异步方法，也需加await（参考历史改造）
    await user_service.update_last_login(user_id=user.id)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


# 关键4：test_token接口依赖的CurrentUser需同步改造（见步骤3）
@router.post("/login/test-token", response_model=UserOut)
async def test_token(  # 改def→async def
    current_user: CurrentUser
) -> Any:
    """测试Token有效性（异步实现）"""
    return current_user


# 关键5：recover_password接口（调用异步user_service.get_user_by_email）
@router.post("/password-recovery/{email}")
@inject
async def recover_password(  # 改def→async def
    email: str,
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> Message:
    """密码找回（异步实现）"""
    # 调用异步方法加await
    user = await user_service.get_user_by_email(email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )

    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


# 关键6：reset_password接口（调用异步auth_service.get_current_user）
@router.post("/reset-password/")
@inject
async def reset_password(  # 改def→async def
    body: NewPassword,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep
) -> Message:
    """重置密码（异步实现）"""
    # 调用异步方法加await
    user = await auth_service.get_current_user(token=body.token)
    # 调用异步方法加await
    return await user_service.update_password(user_id=user.id, new_password=body.new_password)

# 关键7：recover_password_html_content接口
@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
@inject
async def recover_password_html_content(  # 改def→async def
    email: str,
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> Any:
    """密码找回HTML内容（异步实现）"""
    user = await user_service.get_user_by_email(email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )

    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    return HTMLResponse(
        content=email_data.html_content, headers={"subject": email_data.subject}
    )