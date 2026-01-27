"""
数据字典相关的Pydantic Schemas
backend/app/schemas/sys_dict.py
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid

from app.schemas.base import BaseSchema


class DictTypeBase(BaseSchema):
    """字典类型基础模型"""
    dict_code: Optional[str] = Field(None, description="类型编码", example="gender")
    name: Optional[str] = Field(None, description="类型名称", example="性别")
    status: Optional[int] = Field(0, description="状态(0:正常;1:禁用)")
    remark: Optional[str] = Field(None, description="备注")


class DictTypeCreate(DictTypeBase):
    """创建字典类型模型"""
    dict_code: str = Field(..., description="类型编码", example="gender")
    name: str = Field(..., description="类型名称", example="性别")


class DictTypeUpdate(DictTypeBase):
    """更新字典类型模型"""
    pass


class DictTypeOut(DictTypeBase):
    """字典类型输出模型"""
    id: str = Field(..., description="字典类型ID")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            uuid.UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class DictItemBase(BaseSchema):
    """字典项基础模型"""
    dict_code: Optional[str] = Field(None, description="关联字典编码", example="gender")
    value: Optional[str] = Field(None, description="字典项值", example="1")
    label: Optional[str] = Field(None, description="字典项标签", example="男")
    tag_type: Optional[str] = Field(None, description="标签类型", example="success")
    status: Optional[int] = Field(0, description="状态（1-正常，0-禁用）")
    sort: Optional[int] = Field(0, description="排序")
    remark: Optional[str] = Field(None, description="备注")


class DictItemCreate(DictItemBase):
    """创建字典项模型"""
    dict_code: str = Field(..., description="关联字典编码", example="gender")
    value: str = Field(..., description="字典项值", example="1")
    label: str = Field(..., description="字典项标签", example="男")


class DictItemUpdate(DictItemBase):
    """更新字典项模型"""
    pass


class DictItemOut(DictItemBase):
    """字典项输出模型"""
    id: str = Field(..., description="字典项ID")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            uuid.UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class DictItemOption(BaseSchema):
    """字典项选项模型（用于前端下拉框）"""
    value: str = Field(..., description="字典项值", example="1")
    label: str = Field(..., description="字典项标签", example="男")
    tag_type: Optional[str] = Field(None, description="标签类型", example="success")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            uuid.UUID: lambda v: str(v),
        }
    )


class DictTypeWithItems(DictTypeOut):
    """字典类型及其项列表"""
    items: List[DictItemOption] = Field(default_factory=list, description="字典项列表")


class DictItemList(BaseSchema):
    """字典项列表响应"""
    items: List[DictItemOut]
    total: int


class DictTypeList(BaseSchema):
    """字典类型列表响应"""
    items: List[DictTypeOut]
    total: int