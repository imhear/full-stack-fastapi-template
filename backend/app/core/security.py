"""
权限相关核心文件
backend/app/core/security.py
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from jose import jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

ALGORITHM = f"{settings.ALGORITHM}"

# ------------------------------
# 密码加密上下文（保持不变）
# ------------------------------
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)

# ------------------------------
# OAuth2配置（保持不变）
# ------------------------------
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    scheme_name="OAuth2PasswordBearer"
)

# ------------------------------
# 核心修复1：密码加密（截断到72字节）
# ------------------------------
def get_password_hash(password: str) -> str:
    """
    加密密码：
    1. 将字符串密码编码为UTF-8字节（处理中文/特殊字符）
    2. 截断到72字节（符合bcrypt限制）
    3. 哈希处理
    """
    # 关键步骤：编码+截断（72字节限制）
    password_bytes = password.encode("utf-8")[:72]  # 先编码再截断
    return pwd_context.hash(password_bytes)  # 用截断后的字节哈希

# ------------------------------
# 核心修复2：密码验证（与加密逻辑一致）
# ------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码：
    1. 明文密码按加密逻辑同样编码+截断
    2. 与数据库中的哈希值比对
    """
    # 关键步骤：保持与加密一致的编码+截断
    plain_password_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(plain_password_bytes, hashed_password)

# ------------------------------
# Token生成/解析（保持不变）
# ------------------------------
def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_jwt_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])