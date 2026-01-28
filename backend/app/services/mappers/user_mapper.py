"""
backend/app/services/mappers/user_mapper.py
用户字段映射器 - 重构版（策略模式实现）

设计原则：
1. 单一职责：每个类/模块只做一件事
2. 开放封闭：新增格式不需修改现有代码
3. 依赖倒置：依赖抽象，不依赖具体实现
4. 组合优于继承：使用策略模式组合行为
"""
from typing import Dict, Any, List, Optional
from app.models import SysUser
from .constants import FormatType, DEBUG_CONFIG
from .base import FormatStrategy
from .strategies import (
    UserMeResponseStrategy,
    UserProfileStrategy,
    UserListItemStrategy,
    UserDetailStrategy,
    UserFormStrategy
)
from .extractors import UserBaseDataExtractor


class UserFieldMapper:
    """
    用户字段映射器 - 策略模式实现

    职责：协调各个策略完成用户数据转换
    """

    def __init__(self, debug: bool = None):
        """
        初始化用户字段映射器

        Args:
            debug: 是否启用调试模式，默认使用配置
        """
        self.debug = debug if debug is not None else DEBUG_CONFIG['enabled']

        # 初始化数据提取器
        self.base_extractor = UserBaseDataExtractor()

        # 注册所有格式策略
        self._strategies: Dict[str, FormatStrategy] = {}
        self._register_strategies()

        # 缓存策略实例
        self._strategy_cache = {}

    def _register_strategies(self):
        """注册所有格式策略"""
        strategies = [
            UserMeResponseStrategy(debug=self.debug),
            UserProfileStrategy(debug=self.debug),
            UserListItemStrategy(debug=self.debug),
            UserDetailStrategy(debug=self.debug),
            UserFormStrategy(debug=self.debug),
        ]

        for strategy in strategies:
            self._strategies[strategy.format_name()] = strategy

    def _get_strategy(self, format_type: str) -> Optional[FormatStrategy]:
        """
        获取指定格式的策略

        Args:
            format_type: 格式类型

        Returns:
            格式策略实例，如果找不到返回None
        """
        # 使用缓存提高性能
        if format_type not in self._strategy_cache:
            strategy = self._strategies.get(format_type)
            if not strategy:
                raise ValueError(f"未知的格式类型: {format_type}")
            self._strategy_cache[format_type] = strategy

        return self._strategy_cache[format_type]

    # ==================== 主要转换方法 ====================

    def to_user_me_response(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为当前登录用户信息格式（UserMeResponse）

        Args:
            user: SysUser ORM对象

        Returns:
            UserMeResponse格式的字典
        """
        return self._convert_to_format(user, FormatType.ME_RESPONSE)

    def to_user_profile(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为个人中心信息格式

        Args:
            user: SysUser ORM对象

        Returns:
            个人中心信息格式的字典
        """
        return self._convert_to_format(user, FormatType.PROFILE)

    def to_user_list_item(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为用户列表项格式

        Args:
            user: SysUser ORM对象

        Returns:
            列表项格式的字典
        """
        return self._convert_to_format(user, FormatType.LIST_ITEM)

    def to_user_detail(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为用户详情格式（用于创建/更新后返回）

        Args:
            user: SysUser ORM对象

        Returns:
            详情格式的字典
        """
        return self._convert_to_format(user, FormatType.DETAIL)

    def to_user_form(self, user: SysUser) -> Dict[str, Any]:
        """
        转换为用户表单格式（用于前端编辑）

        Args:
            user: SysUser ORM对象

        Returns:
            用户表单格式的字典，包含roleIds字段
        """
        return self._convert_to_format(user, FormatType.FORM)

    def to_users_list(self, users: List[SysUser]) -> List[Dict[str, Any]]:
        """
        批量转换为用户列表格式

        Args:
            users: SysUser ORM对象列表

        Returns:
            用户列表格式的字典列表
        """
        return [self.to_user_list_item(user) for user in users]

    # ==================== 核心转换逻辑 ====================

    def _convert_to_format(self, user: SysUser, format_type: str) -> Dict[str, Any]:
        """
        根据格式类型转换用户对象（策略模式实现）

        Args:
            user: SysUser ORM对象
            format_type: 格式类型

        Returns:
            转换后的数据字典

        Raises:
            ValueError: 格式类型不支持
        """
        # 1. 提取基础数据
        base_data = self.base_extractor.extract(user)

        # 2. 获取对应策略
        strategy = self._get_strategy(format_type)

        # 3. 使用策略转换数据
        return strategy.transform(base_data, user)

    # ==================== 扩展方法 ====================

    def register_strategy(self, strategy: FormatStrategy):
        """
        注册新的格式策略

        Args:
            strategy: 格式策略实例
        """
        format_name = strategy.format_name()
        self._strategies[format_name] = strategy
        # 清除缓存
        self._strategy_cache.pop(format_name, None)

    def get_available_formats(self) -> List[str]:
        """
        获取所有支持的格式类型

        Returns:
            支持的格式类型列表
        """
        return list(self._strategies.keys())


# 全局用户映射器实例
user_mapper = UserFieldMapper()