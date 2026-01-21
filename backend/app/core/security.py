"""
权限相关核心文件
backend/app/core/security.py
更新：添加刷新令牌功能
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

ALGORITHM = f"{settings.ALGORITHM}"

# ------------------------------
# 密码加密上下文
# ------------------------------
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)

# ------------------------------
# OAuth2配置
# ------------------------------
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    scheme_name="OAuth2PasswordBearer"
)

# ------------------------------
# 密码加密（截断到72字节）
# ------------------------------
def get_password_hash(password: str) -> str:
    """
    加密密码：
    1. 将字符串密码编码为UTF-8字节（处理中文/特殊字符）
    2. 截断到72字节（符合bcrypt限制）
    3. 哈希处理
    """
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes)

# ------------------------------
# 密码验证
# ------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码：
    1. 明文密码按加密逻辑同样编码+截断
    2. 与数据库中的哈希值比对
    """
    plain_password_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(plain_password_bytes, hashed_password)

# ------------------------------
# Token生成/解析
# ------------------------------
def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌（Access Token）
    通常过期时间较短（如30分钟）
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建刷新令牌（Refresh Token）
    通常过期时间较长（如7天）

    Args:
        data: 要编码到token中的数据，必须包含'sub'字段
        expires_delta: 过期时间，默认为7天

    Returns:
        str: JWT刷新令牌
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 默认7天过期
        expire = datetime.utcnow() + timedelta(days=7)

    # 确保数据包含子主题
    if "sub" not in data:
        raise ValueError("Refresh token data must contain 'sub' field")

    # 添加过期时间和token类型
    to_encode = data.copy()
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_jwt_token(token: str) -> dict[str, Any]:
    """
    解码JWT令牌

    Returns:
        dict: 解码后的payload

    Raises:
        JWTError: 如果token无效或已过期
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def verify_token(token: str) -> Dict[str, Any]:
    """
    验证JWT令牌并返回payload

    Args:
        token: JWT令牌字符串

    Returns:
        dict: 解码后的payload

    Raises:
        JWTError: 如果token无效或已过期
    """
    try:
        payload = decode_jwt_token(token)
        return payload
    except JWTError as e:
        raise JWTError(f"Token验证失败: {str(e)}")

def extract_token_subject(token: str) -> str:
    """
    从token中提取subject（用户ID）

    Args:
        token: JWT令牌

    Returns:
        str: 用户ID

    Raises:
        JWTError: 如果token无效或已过期
    """
    payload = verify_token(token)
    return payload.get("sub")

def is_refresh_token(token: str) -> bool:
    """
    检查token是否为刷新令牌

    Args:
        token: JWT令牌

    Returns:
        bool: 如果是刷新令牌返回True

    Raises:
        JWTError: 如果token无效或已过期
    """
    payload = verify_token(token)
    return payload.get("type") == "refresh"

def is_access_token(token: str) -> bool:
    """
    检查token是否为访问令牌

    Args:
        token: JWT令牌

    Returns:
        bool: 如果是访问令牌返回True

    Raises:
        JWTError: 如果token无效或已过期
    """
    payload = verify_token(token)
    return payload.get("type") == "access"

def refresh_access_token(refresh_token: str) -> str:
    """
    使用刷新令牌获取新的访问令牌

    Args:
        refresh_token: 有效的刷新令牌

    Returns:
        str: 新的访问令牌

    Raises:
        JWTError: 如果刷新令牌无效或已过期
        ValueError: 如果刷新令牌不是刷新类型
    """
    # 验证刷新令牌
    payload = verify_token(refresh_token)

    # 确保是刷新令牌
    if payload.get("type") != "refresh":
        raise ValueError("Token is not a refresh token")

    # 提取用户ID
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Refresh token does not contain user ID")

    # 创建新的访问令牌（30分钟过期）
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(user_id, expires_delta)