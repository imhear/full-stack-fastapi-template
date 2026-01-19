# app/services/role_service.py
from typing import Optional, List
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import SysRole
from app.repositories.sys_user_repository import UserRepository
from app.repositories.sys_role_repository import RoleRepository
from app.repositories.sys_permission_repository import PermissionRepository
from app.schemas.sys_role import RoleCreate, RoleUpdate
from app.schemas.sys_user import Message
from app.core.exceptions import ResourceNotFound, BadRequest


class RoleService:
    """角色Service层：仅管业务逻辑"""
    def __init__(
            self,
            role_repository: RoleRepository,
            permission_repository: PermissionRepository,
            user_repository: UserRepository,
            async_db_session: AsyncSession
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.user_repository = user_repository
        self.async_db_session = async_db_session

    # ------------------------------
    # 核心业务：创建角色
    # ------------------------------
    async def create_role(self, role_in: RoleCreate) -> SysRole:
        """创建角色（含权限分配，业务校验+调用Repo）"""
        # 1. 业务校验1：角色编码唯一性
        existing_role = await self.role_repository.get_by_code(code=role_in.code)
        if existing_role:
            raise BadRequest(detail=f"Role code '{role_in.code}' already exists")

        # 2. 业务校验2：权限ID有效性（若传了权限）
        valid_perm_ids = []
        if role_in.permission_ids:
            valid_perm_ids = await self.permission_repository.get_existing_ids(
                permission_ids=role_in.permission_ids
            )
            # 若存在无效ID，抛异常
            invalid_ids = set(role_in.permission_ids) - valid_perm_ids
            if invalid_ids:
                raise BadRequest(detail=f"Invalid permission IDs: {', '.join(invalid_ids)}")

        # 3. 调用Repo创建角色
        async with self.role_repository.transaction() as session:
            new_role = await self.role_repository.create(
                role_in=role_in,
                session=session
            )

        # 4. 友好提示：若传了权限但权限表为空
        if role_in.permission_ids and not new_role.permissions:
            raise BadRequest(detail="Cannot assign permissions: permissions table is empty")

        return new_role

    # ------------------------------
    # 基础业务：查询角色
    # ------------------------------
    async def get_role_by_id(self, role_id: str) -> SysRole:
        """按ID查询角色（不存在则抛异常）"""
        role = await self.role_repository.get_by_id(role_id=role_id)
        if not role:
            raise ResourceNotFound(detail=f"Role with ID '{role_id}' not found")
        return role

    async def get_role_by_code(self, code: str) -> Optional[SysRole]:
        """按编码查询角色（不存在返回None）"""
        return await self.role_repository.get_by_code(code=code)

    async def list_roles(self, offset: int = 0, limit: int = 100) -> List[SysRole]:
        """分页查询角色列表"""
        return await self.role_repository.list_all(offset=offset, limit=limit)

    # ------------------------------
    # 基础业务：更新角色
    # ------------------------------
    async def assign_permissions(self, role_id: str, permission_ids: List[str]) -> Message:
        """为角色分配权限（业务校验+调用Repo）"""
        # 1. 业务校验1：角色存在
        await self.get_role_by_id(role_id=role_id)  # 不存在会抛异常

        # 2. 业务校验2：权限ID有效性
        valid_perm_ids = await self.permission_repository.get_existing_ids(
            permission_ids=permission_ids
        )
        invalid_ids = set(permission_ids) - valid_perm_ids
        if invalid_ids:
            raise BadRequest(detail=f"Invalid permission IDs: {', '.join(invalid_ids)}")

        # 3. 调用Repo分配权限
        async with self.role_repository.transaction() as session:
            await self.role_repository.assign_permissions(
                role_id=role_id,
                permission_ids=valid_perm_ids,
                session=session
            )
        return Message(message=f"Permissions assigned successfully to role '{role_id}'")

    async def update_role(self, role_id: str, role_update: RoleUpdate) -> SysRole:
        """更新角色信息（含权限更新）"""
        # 1. 业务校验1：角色存在
        await self.get_role_by_id(role_id=role_id)

        # 2. 业务校验2：角色编码唯一性（若更新编码）
        if role_update.code:
            existing_role = await self.role_repository.get_by_code(code=role_update.code)
            if existing_role and existing_role.id != role_id:
                raise BadRequest(detail=f"Role code '{role_update.code}' already exists")

        # 3. 业务校验3：权限ID有效性（若更新权限）
        if role_update.permission_ids:
            valid_perm_ids = await self.permission_repository.get_existing_ids(
                permission_ids=role_update.permission_ids
            )
            invalid_ids = set(role_update.permission_ids) - valid_perm_ids
            if invalid_ids:
                raise BadRequest(detail=f"Invalid permission IDs: {', '.join(invalid_ids)}")

        # 4. 调用Repo更新
        async with self.role_repository.transaction() as session:
            updated_role = await self.role_repository.update(
                role_id=role_id,
                role_update=role_update,
                session=session
            )
        return updated_role

    # ------------------------------
    # 基础业务：删除角色
    # ------------------------------
    async def delete_role(self, role_id: str) -> Message:
        """删除角色（需校验是否被用户使用）"""
        # 1. 业务校验1：角色存在
        await self.get_role_by_id(role_id=role_id)

        # 2. 业务校验2：角色未被用户使用
        is_in_use = await self.user_repository.check_role_in_use(role_id=role_id)
        if is_in_use:
            raise BadRequest(detail=f"Role '{role_id}' is used by users, cannot delete")

        # 3. 调用Repo删除
        async with self.role_repository.transaction() as session:
            success = await self.role_repository.delete(role_id=role_id, session=session)
            if not success:
                raise ResourceNotFound(detail=f"Role '{role_id}' not found")
        return Message(message=f"Role '{role_id}' deleted successfully")