"""
用户相关的Pydantic Schemas
backend/app/schemas/user.py
上次更新：2025/12/1
"""
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema, TimestampSchema, IDSchema
from app.schemas.sys_role import RoleOut

# 新增：时间转换工具函数
def convert_to_beijing_time(dt: Optional[datetime]) -> Optional[datetime]:
    """将带时区的datetime对象转换为北京时间（Asia/Shanghai）"""
    if dt is None:
        return None
    beijing_tz = ZoneInfo("Asia/Shanghai")
    return dt.astimezone(beijing_tz)

class UserBase(BaseSchema):
    username: str = Field(..., description="用户名", example="john_doe")
    email: EmailStr = Field(..., description="邮箱地址", example="john@example.com")
    full_name: Optional[str] = Field(None, description="全名")

class UserCreate(UserBase):
    password: str = Field(..., description="密码", min_length=6, example="securepassword123")
    role_ids: Optional[List[str]] = Field([], description="角色ID列表")

# 新增：中间模型（仅用于Service→Repo层，携带加密后的密码）
class UserCreateWithHash(UserBase):
    hashed_password: str = Field(..., description="加密后的密码")  # 新增加密密码字段
    role_ids: Optional[List[str]] = Field([], description="角色ID列表")  # 保留角色ID
    # 【核心修复】添加is_active字段，默认值True（与业务逻辑一致）
    is_active: bool = Field(True, description="是否激活，默认True")

class UserUpdate(BaseSchema):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[str]] = None

class UserInDB(UserBase, TimestampSchema, IDSchema):
    is_active: bool = Field(True, description="是否激活")
    is_superuser: bool = Field(False, description="是否为超级用户")

    # 关键：使用自定义验证器转换时间
    last_login: Optional[datetime] = Field(None, description="最后登录时间（北京时间）")
    created_at: datetime = Field(..., description="创建时间（北京时间）")
    updated_at: datetime = Field(..., description="更新时间（北京时间）")

    @model_validator(mode="after")
    def convert_timezones(self):
        """验证后将所有时间字段转换为北京时间"""
        self.last_login = convert_to_beijing_time(self.last_login)
        self.created_at = convert_to_beijing_time(self.created_at)
        self.updated_at = convert_to_beijing_time(self.updated_at)
        return self

# 用于响应，不包含敏感信息
class UserOut(UserInDB):
    roles: List[RoleOut] = Field([], description="用户拥有的角色列表")

class UserWithPermissions(UserOut):
    permissions: List[str] = Field([], description="用户拥有的权限代码列表")

# 用于用户列表响应
class UserList(BaseSchema):
    items: List[UserOut]
    total: int

# 登录相关Schemas
class UserLogin(BaseSchema):
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    username: Optional[str] = None
    user_id: Optional[str] = None

# Generic message
class Message(BaseSchema):
    message: str

class TokenPayload(BaseSchema):
    sub: Optional[str] = None

class NewPassword(BaseSchema):
    token: str
    new_password: str = Field(..., min_length=8, max_length=40)

# class UserUpdateSelfPassword(BaseSchema):
#     password: Optional[str] = None
#     new_password: Optional[str] = None

class UserUpdateSelfPassword(BaseSchema):
    password: Optional[str] = Field(..., description="原密码（至少6位）", min_length=6, max_length=40, example="oldpassword12")
    new_password: Optional[str] = Field(..., description="新密码（至少6位）", min_length=6, max_length=40, example="newpassword12")

# 新增：修改个人密码的请求体模型（遵循现有规范）
class UpdateOwnPassword(BaseSchema):
    old_password: str = Field(..., description="原密码（至少6位）", min_length=6, max_length=40, example="oldpassword123")
    new_password: str = Field(..., description="新密码（至少6位）", min_length=6, max_length=40, example="newpassword123")