"""
backend/app/services/mappers/strategies.py
用户数据格式转换策略
"""
from typing import Dict, Any
from datetime import datetime
from app.models import SysUser
from app.utils.field_mapper import FieldMapper
from .constants import FIELD_MAPPINGS, FormatType
from .extractors import (
    UserBaseDataExtractor,
    UserRoleDataExtractor,
    UserDepartmentDataExtractor
)
from .base import FormatStrategy, DataTransformer


class BaseFormatStrategy(DataTransformer):
    """基础格式策略"""

    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.field_mapper = FieldMapper(FIELD_MAPPINGS)
        self.base_extractor = UserBaseDataExtractor()
        self.role_extractor = UserRoleDataExtractor()
        self.dept_extractor = UserDepartmentDataExtractor()

    def _apply_base_mapping(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用基础字段映射"""
        result = self.field_mapper.backend_to_frontend(base_data)

        # 确保所有必需字段存在
        result.setdefault('avatar', None)
        result.setdefault('deptId', None)

        return result

    def _format_timestamp(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化时间戳"""
        if 'createTime' in result and isinstance(result['createTime'], datetime):
            result['createTime'] = result['createTime'].isoformat()
        return result


class UserMeResponseStrategy(BaseFormatStrategy):
    """用户信息响应格式策略"""

    def format_name(self) -> str:
        return FormatType.ME_RESPONSE

    def transform(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建当前用户响应格式"""
        self._log_debug("Building ME_RESPONSE format", base_data)

        # 应用基础映射
        result = self._apply_base_mapping(base_data)

        # 提取角色和权限
        role_data = self.role_extractor.extract(user)
        result['roles'] = role_data.get('role_codes', [])
        result['perms'] = role_data.get('permission_codes', [])

        # 格式化时间戳
        result = self._format_timestamp(result)

        self._log_debug("ME_RESPONSE result", result)
        return result


class UserProfileStrategy(BaseFormatStrategy):
    """个人中心格式策略"""

    def format_name(self) -> str:
        return FormatType.PROFILE

    def transform(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建个人中心格式"""
        # 应用基础映射
        result = self._apply_base_mapping(base_data)

        # 提取部门信息
        dept_data = self.dept_extractor.extract(user)
        result.update(dept_data)

        # 格式化时间戳
        result = self._format_timestamp(result)

        return result


class UserListItemStrategy(BaseFormatStrategy):
    """列表项格式策略"""

    def format_name(self) -> str:
        return FormatType.LIST_ITEM

    def transform(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建列表项格式"""
        # 应用基础映射
        result = self._apply_base_mapping(base_data)

        # 提取部门信息
        dept_data = self.dept_extractor.extract(user)
        result.update(dept_data)

        # 格式化时间戳
        result = self._format_timestamp(result)

        return result


class UserDetailStrategy(BaseFormatStrategy):
    """用户详情格式策略"""

    def format_name(self) -> str:
        return FormatType.DETAIL

    def transform(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建用户详情格式"""
        # 应用基础映射
        result = self._apply_base_mapping(base_data)

        # 提取角色数据
        role_data = self.role_extractor.extract(user)
        result['roles'] = role_data.get('role_codes', [])
        result['perms'] = role_data.get('permission_codes', [])

        # 格式化时间戳
        result = self._format_timestamp(result)

        return result


class UserFormStrategy(BaseFormatStrategy):
    """用户表单格式策略"""

    def format_name(self) -> str:
        return FormatType.FORM

    def transform(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """构建用户表单格式"""
        # 应用基础映射
        result = self._apply_base_mapping(base_data)

        # 提取角色ID列表
        role_data = self.role_extractor.extract(user)
        result['roleIds'] = role_data.get('role_ids', [])

        # 添加openId字段（数据库字段是openid）
        if hasattr(user, 'openid'):
            result['openId'] = user.openid

        # 格式化时间戳
        result = self._format_timestamp(result)

        return result