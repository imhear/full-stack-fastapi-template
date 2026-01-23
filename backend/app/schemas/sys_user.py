"""
用户相关的Pydantic Schemas
backend/app/schemas/sys_user.py
上次更新：2025/12/1
"""
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, EmailStr, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid

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


# ============ 新增：用户信息响应模型（用于 /me 接口）============
class UserMeResponse(BaseSchema):
    """
    用户信息响应模型 - 专为前端设计

    注意：字段名与前端 TypeScript 定义保持一致
    """
    # 必需字段
    userId: str = Field(..., description="用户ID", examples=["22222222-3333-4444-5555-666666666666"])
    username: str = Field(..., description="用户名", example="admin")
    nickname: str = Field(..., description="用户昵称", example="系统管理员")
    avatar: Optional[str] = Field(None, description="用户头像URL", example="https://example.com/avatar.jpg")
    roles: List[str] = Field(default_factory=list, description="角色代码列表", example=["ADMIN"])
    perms: List[str] = Field(default_factory=list, description="权限代码列表", example=["user:read", "user:create"])

    # 可选字段
    gender: Optional[int] = Field(None, description="性别(1-男 2-女 0-保密)", example=1)
    mobile: Optional[str] = Field(None, description="手机号", example="18812345678")
    email: Optional[str] = Field(None, description="邮箱", example="youlaitech@163.com")
    status: int = Field(1, description="状态(1-正常 0-禁用)", example=1)
    deptId: Optional[str] = Field(None, description="部门ID", examples=["11111111-1111-1111-1111-111111111111"])
    createTime: Optional[datetime] = Field(None, description="创建时间")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 对象转换
        populate_by_name=True,  # 允许使用别名
        json_encoders={
            uuid.UUID: lambda v: str(v),  # UUID 转换为字符串
            datetime: lambda v: v.isoformat() if v else None  # datetime 转换为 ISO 字符串
        }
    )

    @model_validator(mode="before")
    @classmethod
    def ensure_uuid_string(cls, data):
        """确保所有 UUID 字段都转换为字符串"""
        if isinstance(data, dict):
            # 处理 UUID 字段
            uuid_fields = ['userId', 'deptId']
            for field in uuid_fields:
                if field in data and data[field] and isinstance(data[field], uuid.UUID):
                    data[field] = str(data[field])

            # 处理嵌套的 UUID
            if 'id' in data and data['id'] and isinstance(data['id'], uuid.UUID):
                data['userId'] = str(data['id'])

        return data

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