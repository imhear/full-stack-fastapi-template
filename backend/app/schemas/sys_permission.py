"""
权限相关的Pydantic Schemas
backend/app/schemas/permission.py
上次更新：2025/12/1
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema, TimestampSchema, IDSchema

class PermissionBase(BaseSchema):
    code: str = Field(..., description="权限代码", example="user:create")
    name: str = Field(..., description="权限名称", example="创建用户")
    description: Optional[str] = Field(None, description="权限描述")
    category: Optional[str] = Field("general", description="权限分类")
    module: Optional[str] = Field(None, description="所属模块")
    is_active: bool = Field(True, description="是否激活")

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    module: Optional[str] = None
    is_active: Optional[bool] = None

class PermissionInDB(PermissionBase, TimestampSchema, IDSchema):
    is_system: bool = Field(False, description="是否为系统内置权限")

class PermissionOut(PermissionInDB):
    pass

# 用于权限列表响应
class PermissionList(BaseSchema):
    items: List[PermissionOut]
    total: int