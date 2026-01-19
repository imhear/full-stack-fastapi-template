"""
改造后的权限声明装饰器，避免与依赖注入冲突
backend/app/utils/permission_decorators.py
上次更新：2025/12/1
"""
from functools import wraps
from typing import Callable, Optional, Dict, Any, List
import inspect
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

# 全局权限注册表
_permission_registry = {}


def permission(
        code: str,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = "api",
        auto_register: bool = True
):
    """
    改造后的权限声明装饰器

    关键改变：不再包装函数，只添加元数据
    """

    def decorator(func: Callable) -> Callable:
        # 保存权限元数据到函数属性
        if not hasattr(func, '__api_permissions__'):
            func.__api_permissions__ = []

        permission_data = {
            'code': code,
            'name': name,
            'description': description,
            'category': category,
            'auto_register': auto_register,
            'endpoint': f"{func.__module__}.{func.__qualname__}"
        }

        func.__api_permissions__.append(permission_data)

        # 注册到全局权限表
        if auto_register:
            _permission_registry[code] = permission_data

        # 关键改变：直接返回原始函数，不进行包装
        return func

    return decorator


def get_permission_registry() -> Dict[str, Dict]:
    """获取全局权限注册表"""
    return _permission_registry.copy()


def get_endpoint_permissions(func: Callable) -> List[Dict]:
    """获取端点声明的权限"""
    return getattr(func, '__api_permissions__', [])