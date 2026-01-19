# app/schemas/relationship.py
"""
关联关系相关的Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

from app.schemas.base import BaseSchema

class UserRoleAssignment(BaseSchema):
    user_id: str = Field(..., description="用户ID")
    role_ids: List[str] = Field(..., description="角色ID列表")

class RolePermissionAssignment(BaseSchema):
    role_id: str = Field(..., description="角色ID")
    permission_ids: List[str] = Field(..., description="权限ID列表")

class UserRoleResponse(BaseSchema):
    user_id: str
    role_id: str
    created_at: datetime

class RolePermissionResponse(BaseSchema):
    role_id: str
    permission_id: str
    created_at: datetime