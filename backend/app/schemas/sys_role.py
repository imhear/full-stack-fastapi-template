"""
角色相关的Pydantic Schemas
backend/app/schemas/role.py
上次更新：2025/12/1
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema, TimestampSchema, IDSchema
from app.schemas.sys_permission import PermissionOut

class RoleBase(BaseSchema):
    name: str = Field(..., description="角色名称", example="管理员")
    code: str = Field(..., description="角色代码", example="admin")
    description: Optional[str] = Field(None, description="角色描述")
    is_active: bool = Field(True, description="是否激活")

class RoleCreate(RoleBase):
    permission_ids: Optional[List[str]] = Field([], description="权限ID列表")

class RoleUpdate(BaseSchema):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[str]] = None

class RoleInDB(RoleBase, TimestampSchema, IDSchema):
    is_system: bool = Field(False, description="是否为系统内置角色")

class RoleOut(RoleInDB):
    permissions: List[PermissionOut] = Field([], description="角色拥有的权限列表")

class RoleWithUsers(RoleOut):
    user_count: int = Field(0, description="拥有该角色的用户数量")

# 用于角色列表响应
class RoleList(BaseSchema):
    items: List[RoleOut]
    total: int