"""
backend/app/services/mappers/user_mapper.py
上次更新：2026/1/21
用户字段映射器 - 重构版（完全职责分离）

设计原则：
1. 单一职责：只处理用户数据结构转换
2. 完备性：覆盖所有用户相关的转换场景
3. 无副作用：不处理业务逻辑，只做数据清洗
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from app.models import SysUser
from app.utils.field_mapper import FieldMapper


class UserFieldMapper:
    """
    用户字段映射器 - 增强版（支持所有转换场景）

    职责：所有用户数据结构的转换都在这里完成
    """

    def __init__(self):
        # 基础字段映射配置
        self._field_mapper = FieldMapper({
            # 用户标识
            'id': 'userId',

            # 时间字段
            'create_time': 'createTime',
            'update_time': 'updateTime',
            'last_login': 'lastLogin',

            # 组织字段
            'dept_id': 'deptId',
            'dept_name': 'deptName',

            # 个人信息
            'status': 'status',
            'role_ids': 'roleIds',
        })

    # ==================== 主要转换方法 ====================

    def to_user_me_response(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为当前登录用户信息格式（UserMeResponse）

        Args:
            user: SysUser ORM对象

        Returns:
            UserMeResponse格式的字典
        """
        return self._convert_to_format(user, 'me_response')

    def to_user_profile(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为个人中心信息格式

        Args:
            user: SysUser ORM对象

        Returns:
            个人中心信息格式的字典
        """
        return self._convert_to_format(user, 'profile')

    def to_user_list_item(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为用户列表项格式

        Args:
            user: SysUser ORM对象

        Returns:
            列表项格式的字典
        """
        return self._convert_to_format(user, 'list_item')

    def to_user_detail(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为用户详情格式（用于创建/更新后返回）

        Args:
            user: SysUser ORM对象

        Returns:
            详情格式的字典
        """
        return self._convert_to_format(user, 'detail')

    def to_users_list(self, users: List[SysUser]) -> List[Dict[str, Any]]:
        """
        批量转换为用户列表格式

        Args:
            users: SysUser ORM对象列表

        Returns:
            用户列表格式的字典列表
        """
        return [self.to_user_list_item(user) for user in users]

    # ==================== 格式配置 ====================

    def _convert_to_format(self, user: SysUser, format_type: str) -> Dict[str, Any]:
        """
        根据格式类型转换用户对象

        这是内部方法，对外暴露具体格式的方法
        """
        # 基础数据提取
        base_data = self._extract_base_data(user)

        # 根据格式类型添加特定字段
        if format_type == 'me_response':
            return self._build_me_response(base_data, user)
        elif format_type == 'profile':
            return self._build_profile(base_data, user)
        elif format_type == 'list_item':
            return self._build_list_item(base_data, user)
        elif format_type == 'detail':
            return self._build_detail(base_data, user)
        else:
            raise ValueError(f"未知的格式类型: {format_type}")

    def _extract_base_data(self, user: SysUser) -> Dict[str, Any]:
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

    def _build_me_response(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建当前用户响应格式"""
        print(f"[DEBUG] base_data keys: {list(base_data.keys())}")
        print(f"[DEBUG] base_data: {base_data}")

        result = self._field_mapper.backend_to_frontend(base_data)

        print(f"[DEBUG] after mapping result keys: {list(result.keys())}")
        print(f"[DEBUG] after mapping result: {result}")

        # 提取角色和权限
        result['roles'] = self._extract_role_codes(user)
        result['perms'] = self._extract_permission_codes(user)

        # 确保所有必需字段存在
        result.setdefault('avatar', None)
        result.setdefault('deptId', None)

        print(f"[DEBUG] final result: {result}")
        return result

    # def _build_me_response(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
    #     """构建当前用户响应格式"""
    #     result = self._field_mapper.backend_to_frontend(base_data)
    #
    #     # 提取角色和权限
    #     result['roles'] = self._extract_role_codes(user)
    #     result['perms'] = self._extract_permission_codes(user)
    #
    #     # 确保所有必需字段存在
    #     result.setdefault('avatar', None)
    #     result.setdefault('deptId', None)
    #
    #     return result

    def _build_profile(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建个人中心格式"""
        result = self._field_mapper.backend_to_frontend(base_data)

        # 添加部门信息
        if hasattr(user, 'dept') and user.dept:
            result['deptName'] = user.dept.name

        # 添加角色信息
        if hasattr(user, 'roles') and user.roles:
            role_names = [role.name for role in user.roles if hasattr(role, 'name')]
            result['roleNames'] = ', '.join(role_names)

        # 时间格式处理
        if 'createTime' in result and isinstance(result['createTime'], datetime):
            result['createTime'] = result['createTime'].isoformat()

        return result

    def _build_list_item(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建列表项格式"""
        result = self._field_mapper.backend_to_frontend(base_data)

        # 添加部门信息
        if hasattr(user, 'dept') and user.dept and hasattr(user.dept, 'name'):
            result['deptName'] = user.dept.name

        # 添加角色名称
        if hasattr(user, 'roles') and user.roles:
            role_names = [role.name for role in user.roles if hasattr(role, 'name')]
            result['roleNames'] = ', '.join(role_names)

        # 时间格式处理
        if 'createTime' in result and isinstance(result['createTime'], datetime):
            result['createTime'] = result['createTime'].isoformat()

        return result

    def _build_detail(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建用户详情格式"""
        result = self._field_mapper.backend_to_frontend(base_data)

        # 提取角色和权限
        result['roles'] = self._extract_role_codes(user)
        result['perms'] = self._extract_permission_codes(user)

        # 时间格式处理
        if 'createTime' in result and isinstance(result['createTime'], datetime):
            result['createTime'] = result['createTime'].isoformat()

        return result

    # ==================== 辅助方法 ====================

    def _extract_role_codes(self, user: SysUser) -> List[str]:
        """提取角色代码"""
        role_codes = []
        if hasattr(user, 'roles') and user.roles:
            for role in user.roles:
                if hasattr(role, 'code'):
                    role_codes.append(role.code)
        return role_codes

    def _extract_permission_codes(self, user: SysUser) -> List[str]:
        """提取权限代码"""
        permission_codes = set()
        if hasattr(user, 'roles') and user.roles:
            for role in user.roles:
                if hasattr(role, 'permissions'):
                    for perm in role.permissions:
                        if hasattr(perm, 'code'):
                            permission_codes.add(perm.code)
        return list(permission_codes)


# 全局用户映射器实例
user_mapper = UserFieldMapper()