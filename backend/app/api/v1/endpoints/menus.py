from typing import List, Any
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser

router = APIRouter(prefix="/menus", tags=["menus"])


# 定义前端期望的路由结构
class RouteMeta(BaseModel):
    title: str
    icon: str = ""
    hidden: bool = False
    alwaysShow: bool = False
    noCache: bool = False
    breadcrumb: bool = True
    affix: bool = False
    activeMenu: str = ""
    elSvgIcon: str = ""
    permissions: List[str] = []


class RouteItem(BaseModel):
    path: str
    component: str
    redirect: str = ""
    name: str = ""
    meta: RouteMeta
    children: List[Any] = []


@router.get("/routes")
async def get_menu_routes(
        current_user: CurrentUser,
) -> JSONResponse:
    """
    获取当前用户的菜单路由 - 临时实现，返回基础路由
    返回格式需要匹配前端期望的结构
    """
    try:
        # 根据用户角色返回不同的菜单
        # 这里先返回一个基础的管理后台路由
        routes = []

        # 判断用户角色
        if current_user.status == 1:
            routes = [
                {
                    "path": "/dashboard",
                    "component": "Layout",
                    "redirect": "/dashboard/workplace",
                    "name": "Dashboard",
                    "meta": {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "hidden": False,
                        "alwaysShow": True
                    },
                    "children": [
                        {
                            "path": "workplace",
                            "component": "dashboard/workplace/index",
                            "name": "Workplace",
                            "meta": {
                                "title": "工作台",
                                "icon": "",
                                "hidden": False
                            }
                        }
                    ]
                },
                {
                    "path": "/system",
                    "component": "Layout",
                    "redirect": "/system/user",
                    "name": "System",
                    "meta": {
                        "title": "系统管理",
                        "icon": "system",
                        "hidden": False,
                        "alwaysShow": True
                    },
                    "children": [
                        {
                            "path": "user",
                            "component": "system/user/index",
                            "name": "User",
                            "meta": {
                                "title": "用户管理",
                                "icon": "",
                                "hidden": False
                            }
                        },
                        {
                            "path": "user/recycle-bin",
                            "component": "system/user/RecycleBin",
                            "name": "SystemUserRecycleBin",
                            "meta": {
                                "title": "用户回收站",
                                "icon": "",
                                "hidden": False
                            }
                        },
                        {
                            "path": "role",
                            "component": "system/role/index",
                            "name": "Role",
                            "meta": {
                                "title": "角色管理",
                                "icon": "",
                                "hidden": False
                            }
                        },
                        {
                            "path": "menu",
                            "component": "system/menu/index",
                            "name": "Menu",
                            "meta": {
                                "title": "菜单管理",
                                "icon": "",
                                "hidden": False
                            }
                        }
                    ]
                }
            ]
            # 管理员路由
        else:
            # 普通用户路由
            routes = [
                {
                    "path": "/dashboard",
                    "component": "Layout",
                    "redirect": "/dashboard/workplace",
                    "name": "Dashboard",
                    "meta": {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "hidden": False,
                        "alwaysShow": True
                    },
                    "children": [
                        {
                            "path": "workplace",
                            "component": "dashboard/workplace/index",
                            "name": "Workplace",
                            "meta": {
                                "title": "工作台",
                                "icon": "",
                                "hidden": False
                            }
                        }
                    ]
                }
            ]

        return JSONResponse({
            "code": "00000",
            "msg": "操作成功",
            "data": routes
        })

    except Exception as e:
        return JSONResponse({
            "code": "500",
            "msg": f"获取菜单失败: {str(e)}",
            "data": None
        }, status_code=500)