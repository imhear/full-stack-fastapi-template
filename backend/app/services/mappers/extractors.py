"""
backend/app/services/mappers/extractors.py
用户数据提取器
"""
from typing import Dict, Any, List
from datetime import datetime
from app.models import SysUser
from .base import BaseExtractor


class UserBaseDataExtractor(BaseExtractor):
    """基础用户数据提取器"""

    def extract(self, user: SysUser) -> Dict[str, Any]:
        """
        提取基础用户数据（所有格式共用）
        """
        # 从ORM对象提取数据（确保类型安全）
        data = {
            'id': str(user.id) if user.id else None,
            'username': user.username,
            'nickname': user.nickname or user.username,  # 默认值处理
            'avatar': user.avatar,
            'gender': user.gender,
            'mobile': user.mobile,
            'email': user.email,
            'status': user.status,
            'dept_id': str(user.dept_id) if user.dept_id else None,
            'create_time': user.create_time,
        }

        # 清理None值
        return {k: v for k, v in data.items() if v is not None}


class UserRoleDataExtractor(BaseExtractor):
    """用户角色数据提取器"""

    def extract_role_codes(self, user: SysUser) -> List[str]:
        """提取角色代码"""
        role_codes = []
        if hasattr(user, 'roles') and user.roles:
            for role in user.roles:
                if hasattr(role, 'code'):
                    role_codes.append(role.code)
        return role_codes

    def extract_role_ids(self, user: SysUser) -> List[str]:
        """提取角色ID列表"""
        role_ids = []
        if hasattr(user, 'roles') and user.roles:
            for role in user.roles:
                if hasattr(role, 'id'):
                    role_ids.append(str(role.id))
        return role_ids

    def extract_permission_codes(self, user: SysUser) -> List[str]:
        """提取权限代码"""
        permission_codes = set()
        if hasattr(user, 'roles') and user.roles:
            for role in user.roles:
                if hasattr(role, 'permissions'):
                    for perm in role.permissions:
                        if hasattr(perm, 'code'):
                            permission_codes.add(perm.code)
        return list(permission_codes)

    def extract(self, user: SysUser) -> Dict[str, Any]:
        """
        提取角色相关数据
        """
        return {
            'role_codes': self.extract_role_codes(user),
            'role_ids': self.extract_role_ids(user),
            'permission_codes': self.extract_permission_codes(user)
        }


class UserDepartmentDataExtractor(BaseExtractor):
    """用户部门数据提取器"""

    def extract(self, user: SysUser) -> Dict[str, Any]:
        """
        提取部门相关数据
        """
        dept_data = {}

        # 添加部门信息
        if hasattr(user, 'dept') and user.dept:
            dept_data['dept_name'] = user.dept.name
            if hasattr(user.dept, 'id'):
                dept_data['dept_id'] = str(user.dept.id)

        # 添加角色名称
        if hasattr(user, 'roles') and user.roles:
            role_names = [role.name for role in user.roles if hasattr(role, 'name')]
            dept_data['role_names'] = ', '.join(role_names)

        return dept_data