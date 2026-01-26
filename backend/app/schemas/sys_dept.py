# app/schemas/sys_dept.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


class DeptBase(BaseModel):
    """部门基础模型"""
    model_config = ConfigDict(from_attributes=True)

    name: str
    code: str
    parent_id: Optional[UUID] = None
    sort: int = 1
    status: int = 1


class DeptCreate(DeptBase):
    """部门创建模型"""
    pass


class DeptUpdate(BaseModel):
    """部门更新模型"""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[UUID] = None
    sort: Optional[int] = None
    status: Optional[int] = None


class DeptOut(DeptBase):
    """部门输出模型"""
    id: UUID
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    tree_path: Optional[str] = None


class DeptTreeNode(BaseModel):
    """部门树节点模型"""
    model_config = ConfigDict(from_attributes=True)

    value: str  # 部门ID（字符串格式）
    label: str  # 部门名称
    tag: Optional[str] = None  # 标签（可选）
    children: Optional[List["DeptTreeNode"]] = None


class DeptTreeResponse(BaseModel):
    """部门树响应模型"""
    model_config = ConfigDict(from_attributes=True)

    value: str
    label: str
    children: Optional[List["DeptTreeResponse"]] = None


# 更新前向引用
DeptTreeNode.update_forward_refs()
DeptTreeResponse.update_forward_refs()