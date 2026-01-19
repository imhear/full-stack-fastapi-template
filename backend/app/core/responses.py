"""
核心响应格式配置文件
backend/app/core/responses.py
"""
from typing import Any, Optional
from pydantic import BaseModel

class APIResponse(BaseModel):
    """标准化API响应模型"""
    code: int = 200
    message: str = "Success"
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    """标准化错误响应模型"""
    code: int
    message: str
    details: Optional[Any] = None