"""
登录接口文件
backend/app/api/v1/endpoints/login.py
上次更新：2026/1/19
集成Redis服务和验证码功能
"""
from datetime import timedelta
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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
from app.api.deps import CurrentUser, get_current_active_superuser, OAuth2FormDep, AuthServiceDep, UserServiceDep, CaptchaServiceDep

router = APIRouter(tags=["login"])

# 依赖类型注解（简化写法）
# AuthServiceDep = Annotated[AuthService, Depends(Provide[Container.auth_service])]
# UserServiceDep = Annotated[UserService, Depends(Provide[Container.user_service])]
# OAuth2FormDep = Annotated[OAuth2PasswordRequestForm, Depends()]

# 前端登录请求模型（复用你现有方案）
from pydantic import BaseModel
class LoginRequest(BaseModel):
    username: str
    password: str
    captchaId: Optional[str] = ""
    captchaCode: Optional[str] = ""
    tenantId: Optional[int] = None


@router.get("/captcha")
@inject
async def generate_captcha(
        captcha_service: CaptchaServiceDep
) -> JSONResponse:
    """生成验证码"""
    try:
        captcha_data = await captcha_service.generate_captcha()

        return JSONResponse({
            "code": "00000",
            "msg": "操作成功",
            "data": captcha_data
        })

    except Exception as e:
        return JSONResponse({
            "code": "500",
            "msg": f"生成验证码失败: {str(e)}",
            "data": None
        }, status_code=500)


@router.post("/refresh-token")
@inject
async def refresh_token(
        refresh_request: dict,
        auth_service: AuthServiceDep,
        captcha_service: CaptchaServiceDep
) -> JSONResponse:
    """刷新访问令牌"""
    refresh_token = refresh_request.get("refreshToken")

    if not refresh_token:
        return JSONResponse({
            "code": "400",
            "msg": "刷新令牌不能为空",
            "data": None
        }, status_code=400)

    try:
        # 验证刷新令牌
        user_id = security.extract_token_subject(refresh_token)

        # 检查Redis中是否存在该刷新令牌（可选，用于单点登录控制）
        cached_token = await captcha_service.redis_service.get_refresh_token(user_id)
        if cached_token != refresh_token:
            return JSONResponse({
                "code": "401",
                "msg": "刷新令牌无效或已过期",
                "data": None
            }, status_code=401)

        # 使用刷新令牌获取新的访问令牌
        new_access_token = security.refresh_access_token(refresh_token)

        # 可以重新生成刷新令牌（可选，实现滑动过期）
        new_refresh_token = security.create_refresh_token(data={"sub": user_id})

        # 更新Redis中的刷新令牌
        await captcha_service.redis_service.cache_refresh_token(
            user_id, new_refresh_token, 7 * 24 * 3600
        )

        return JSONResponse({
            "code": "00000",
            "msg": "操作成功",
            "data": {
                "accessToken": new_access_token,
                "refreshToken": new_refresh_token,
                "tokenType": "bearer",
                "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        })
    # TODO no class named JWTError
    # except JWTError as e:
    #     return JSONResponse({
    #         "code": "401",
    #         "msg": f"刷新令牌无效: {str(e)}",
    #         "data": None
    #     }, status_code=401)
    except Exception as e:
        return JSONResponse({
            "code": "500",
            "msg": f"刷新令牌失败: {str(e)}",
            "data": None
        }, status_code=500)


# 关键1：接口方法改为async def，支持await调用
@router.post("/login/access-token")
@inject
async def login_access_token(  # 改def→async def
    login_request: LoginRequest,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    captcha_service: CaptchaServiceDep
) -> JSONResponse:
    """用户登录（支持验证码）- 适配前端JSON格式"""
    username = login_request.username
    password = login_request.password
    captcha_id = login_request.captchaId if login_request.captchaId != "" else None
    captcha_code = login_request.captchaCode if login_request.captchaCode != "" else None

    # 检查账号是否被锁定
    security_status = await captcha_service.check_login_security(username)
    if security_status["is_locked"]:
        return JSONResponse({
            "code": "400",
            "msg": "账号已被锁定，请30分钟后再试",
            "data": None
        }, status_code=400)

    # 如果有验证码参数，则验证验证码
    if captcha_id and captcha_code:
        if not await captcha_service.verify_captcha(captcha_id, captcha_code):
            return JSONResponse({
                "code": "400",
                "msg": "验证码错误",
                "data": None
            }, status_code=400)

        # 验证用户凭据（使用现有的AuthService）
        user = await auth_service.authenticate_user(
            email=username, password=password
        )

        if not user:
            # 记录登录失败
            await captcha_service.redis_service.record_login_failure(username)
            failures = security_status["failures"] + 1

            if failures >= 5:
                await captcha_service.redis_service.lock_account(username, 1800)
                return JSONResponse({
                    "code": "400",
                    "msg": "密码错误次数过多，账号已被锁定30分钟",
                    "data": None
                }, status_code=400)

            return JSONResponse({
                "code": "400",
                "msg": "用户名或密码错误",
                "data": None
            }, status_code=400)

        elif not user.is_active:
            return JSONResponse({
                "code": "400",
                "msg": "用户已被禁用",
                "data": None
            }, status_code=400)

    # 登录成功，清除失败记录
    await captcha_service.redis_service.reset_login_failure(username)

    # 更新最后登录时间
    await user_service.update_last_login(user_id=user.id)

    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    # 生成刷新令牌
    refresh_token = security.create_refresh_token(data={"sub": str(user.id)})

    # 存储刷新令牌到Redis
    await captcha_service.redis_service.cache_refresh_token(
        user.id, refresh_token, 7 * 24 * 3600
    )

    # 返回前端要求的格式
    return JSONResponse({
        "code": "00000",
        "msg": "操作成功",
        "data": {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "bearer",
            "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    })


@router.post("/logout")
@inject
async def logout(
        current_user: CurrentUser,
        captcha_service: CaptchaServiceDep
) -> JSONResponse:
    """用户登出"""
    try:
        # 删除Redis中的刷新令牌
        await captcha_service.redis_service.delete_refresh_token(str(current_user.id))

        # 可选：将访问令牌加入黑名单（如果需要立即失效）
        # await captcha_service.redis_service.blacklist_token(access_token)

        return JSONResponse({
            "code": "00000",
            "msg": "登出成功",
            "data": None
        })
    except Exception as e:
        return JSONResponse({
            "code": "500",
            "msg": f"登出失败: {str(e)}",
            "data": None
        }, status_code=500)


# 关键1：接口方法改为async def，支持await调用
@router.post("/login/access-token/old")
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