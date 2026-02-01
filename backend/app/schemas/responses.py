"""
统一API响应模型
backend/app/schemas/responses.py
"""
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """API统一响应格式"""
    code: str = Field(default="00000", description="响应代码")
    data: Optional[T] = Field(default=None, description="响应数据")
    msg: str = Field(default="操作成功", description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }

    @classmethod
    def success(cls, data: T = None, msg: str = "操作成功") -> 'ApiResponse[T]':
        """成功响应快捷方法"""
        return cls(code="00000", data=data, msg=msg)

    @classmethod
    def error(cls, data: T = None, msg: str = "操作失败") -> 'ApiResponse[T]':
        """失败响应快捷方法"""
        return cls(code="10001", data=data, msg=msg)

    # @classmethod
    # def error(cls, code: str, msg: str, data: Any = None) -> 'ApiResponse':
    #     """错误响应快捷方法"""
    #     return cls(code=code, msg=msg, data=data)


class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: str = Field(..., description="错误代码")
    msg: str = Field(..., description="错误消息")
    details: Optional[Any] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now)


# 常用响应代码
class ResponseCode:
    SUCCESS = "00000"
    VALIDATION_ERROR = "10001"
    AUTH_ERROR = "20001"
    PERMISSION_DENIED = "20003"
    NOT_FOUND = "30001"
    INTERNAL_ERROR = "50000"