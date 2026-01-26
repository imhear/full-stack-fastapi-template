"""
API模块统一入口
backend/app/api/main.py
上次更新：2025/12/1
"""
from fastapi import APIRouter

from app.api.v1.endpoints import users,login,roles,menus,depts# items,login, private, , utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(menus.router)
api_router.include_router(depts.router)
# api_router.include_router(utils.router)
# api_router.include_router(items.router)

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
#
