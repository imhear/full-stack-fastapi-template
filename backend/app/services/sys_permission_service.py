# app/services/permission_service.py
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List  # 【修复】添加缺失的导入

from app.repositories.sys_permission_repository import PermissionRepository
from app.models import SysUser, SysPermission  # 【修复】添加Permission模型导入
from app.schemas.sys_user import Message
from app.services.redis_service import RedisService  # 新增：RedisService依赖

class PermissionService:
    """权限Service层：处理权限校验、权限管理"""
    def __init__(self,
                 permission_repository: PermissionRepository,
                 async_db_session: AsyncSession,
                 redis_service: RedisService):  # 新增：RedisService依赖
        self.permission_repository = permission_repository
        self.async_db_session = async_db_session
        self.redis_service = redis_service  # 新增：RedisService实例

    # ------------------------------
    # 核心业务：用户权限校验
    # ------------------------------
    async def check_user_permission(self, user: SysUser, required_perm: str) -> bool:
        """
        校验用户是否有指定权限：
        1. 超级用户默认有所有权限
        2. 普通用户校验角色继承的权限
        3. 支持通配符（如user:*:*匹配所有用户相关权限）
        """
        # 1. 超级用户直接通过
        if user.is_superuser:
            return True

        # 2. 获取用户所有权限编码
        user_perms = await self.permission_repository.get_user_permissions(user_id=user.id)
        if not user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User '{user.id}' has no permissions assigned"
            )

        # 3. 解析权限通配符（支持三级权限：资源:操作:范围）
        perm_parts = required_perm.split(':')
        # 生成通配符匹配规则（精确匹配 → 二级通配 → 一级通配）
        wildcards = [
            required_perm,  # 精确匹配（如user:create:own）
            f"{perm_parts[0]}:{perm_parts[1]}:*" if len(perm_parts) >=2 else f"{perm_parts[0]}:*",  # 二级通配（如user:create:*）
            f"{perm_parts[0]}:*:*" if len(perm_parts) >=3 else f"{perm_parts[0]}:*"  # 一级通配（如user:*:*）
        ]

        # 4. 校验是否有匹配的权限
        if not any(perm in user_perms for perm in wildcards):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Permission denied",
                    "required_permission": required_perm,
                    "user_permissions": sorted(user_perms),  # 排序便于查看
                    "user_id": user.id,
                    "username": user.username
                }
            )

        return True

    # ------------------------------
    # 基础业务：查询权限
    # ------------------------------
    async def get_permission_by_id(self, perm_id: str) -> SysPermission:  # 【修复】添加返回类型
        """按ID查询权限（不存在则抛异常）"""
        perm = await self.permission_repository.get_by_id(perm_id=perm_id)
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission with ID '{perm_id}' not found"
            )
        return perm

    async def get_permission_by_code(self, code: str) -> Optional[SysPermission]:  # 【修复】添加泛型类型
        """按编码查询权限（不存在返回None）"""
        return await self.permission_repository.get_by_code(code=code)

    async def list_permissions(self, offset: int = 0, limit: int = 100) -> List[SysPermission]:  # 【修复】添加泛型类型
        """分页查询所有权限"""
        return await self.permission_repository.list_all(offset=offset, limit=limit)