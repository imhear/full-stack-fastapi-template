"""
核心异常处理配置文件
backend/app/core/exceptions.py
"""

from fastapi import HTTPException, status

class AppException(HTTPException):
    """基础异常类"""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class ResourceNotFound(AppException):
    """资源不存在异常（404）"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class BadRequest(AppException):
    """参数错误/业务错误（400）"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class PermissionDenied(AppException):
    """权限不足（403）"""
    def __init__(self, detail: str = "Not enough privileges"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)