"""
base类
backend/app/schemas/base.py
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True  # 替换原来的orm_mode
        populate_by_name = True

class TimestampSchema(BaseSchema):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class IDSchema(BaseSchema):
    id: str