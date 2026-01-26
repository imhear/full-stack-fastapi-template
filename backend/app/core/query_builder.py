"""
高级查询构建器模块 - 策略模式实现
backend/app/core/query_builder.py
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy.sql import Select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy import or_, and_
from datetime import datetime, timedelta


# ==================== 策略基类 ====================
class BaseFilterStrategy(ABC):
    """过滤策略基类"""

    @abstractmethod
    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        """应用过滤条件到查询"""
        pass

    def validate(self, value: Any) -> bool:
        """验证输入值是否有效"""
        return value is not None and value != ""


# ==================== 具体过滤策略 ====================
class EqualFilter(BaseFilterStrategy):
    """等于过滤"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        return query.filter(self.field == value)


class NotEqualFilter(BaseFilterStrategy):
    """不等于过滤"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        return query.filter(self.field != value)


class LikeFilter(BaseFilterStrategy):
    """模糊匹配（不区分大小写）"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        return query.filter(self.field.ilike(f"%{value}%"))


class MultiFieldKeywordFilter(BaseFilterStrategy):
    """多字段关键词搜索"""

    def __init__(self, fields: List[InstrumentedAttribute]):
        self.fields = fields

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        conditions = []
        for field in self.fields:
            conditions.append(field.ilike(f"%{value}%"))
        return query.filter(or_(*conditions))


class DateTimeRangeFilter(BaseFilterStrategy):
    """日期时间范围过滤"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        if isinstance(value, dict):
            start = value.get('start')
            end = value.get('end')

            if start:
                query = query.filter(self.field >= start)
            if end:
                # 处理结束时间包含当天
                adjusted_end = end + timedelta(days=1) - timedelta(seconds=1)
                query = query.filter(self.field <= adjusted_end)

        return query


class ValueRangeFilter(BaseFilterStrategy):
    """值范围过滤（支持int、float、字符串）"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        if isinstance(value, dict):
            min_val = value.get('min')
            max_val = value.get('max')

            if min_val is not None:
                query = query.filter(self.field >= min_val)
            if max_val is not None:
                query = query.filter(self.field <= max_val)

        return query


class InFilter(BaseFilterStrategy):
    """IN查询过滤"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        if isinstance(value, list) and value:
            return query.filter(self.field.in_(value))
        return query


class BooleanFilter(BaseFilterStrategy):
    """布尔值过滤"""

    def __init__(self, field: InstrumentedAttribute):
        self.field = field

    def apply(self, query: Select, value: Any, **kwargs) -> Select:
        if isinstance(value, bool):
            return query.filter(self.field == value)
        elif isinstance(value, int):
            return query.filter(self.field == (value == 1))
        elif isinstance(value, str):
            return query.filter(self.field == (value.lower() in ['true', '1', 'yes']))
        return query


# ==================== 查询构建器 ====================
class QueryBuilder:
    """高级查询构建器"""

    def __init__(self, model_class):
        self.model_class = model_class
        self.strategies: Dict[str, BaseFilterStrategy] = {}
        self.conditions: List[Dict[str, Any]] = []

    def register_strategy(self, name: str, strategy: BaseFilterStrategy) -> 'QueryBuilder':
        """注册过滤策略"""
        self.strategies[name] = strategy
        return self

    def auto_register_field_strategies(self, fields_config: Dict[str, Dict[str, Any]]) -> 'QueryBuilder':
        """自动注册字段策略"""
        for field_name, config in fields_config.items():
            if hasattr(self.model_class, field_name):
                field = getattr(self.model_class, field_name)

                # 注册等于过滤
                if config.get('allow_equal', True):
                    self.register_strategy(
                        f"{field_name}__eq",
                        EqualFilter(field)
                    )

                # 注册不等于过滤
                if config.get('allow_not_equal', False):
                    self.register_strategy(
                        f"{field_name}__ne",
                        NotEqualFilter(field)
                    )

                # 注册模糊搜索
                if config.get('allow_like', False):
                    self.register_strategy(
                        f"{field_name}__like",
                        LikeFilter(field)
                    )

                # 注册范围查询
                if config.get('allow_range', False):
                    self.register_strategy(
                        f"{field_name}__range",
                        ValueRangeFilter(field)
                    )

        return self

    def filter(self, **kwargs) -> 'QueryBuilder':
        """添加过滤条件（支持链式调用）"""
        for key, value in kwargs.items():
            if value is not None and value != "":
                # 处理列表类型的空值
                if isinstance(value, list) and not value:
                    continue
                self.conditions.append({"key": key, "value": value})
        return self

    def build(self, base_query: Select) -> Select:
        """构建查询"""
        query = base_query

        for condition in self.conditions:
            key = condition["key"]
            value = condition["value"]

            if key in self.strategies:
                strategy = self.strategies[key]
                if strategy.validate(value):
                    query = strategy.apply(query, value)

        return query

    def reset(self) -> 'QueryBuilder':
        """重置构建器状态"""
        self.conditions.clear()
        return self


# ==================== 分页查询构建器 ====================
class PaginatedQueryBuilder(QueryBuilder):
    """支持分页的查询构建器"""

    def __init__(self, model_class):
        super().__init__(model_class)
        self._offset = 0
        self._limit = 100
        self._order_by = []

    def paginate(self, offset: int = 0, limit: int = 100) -> 'PaginatedQueryBuilder':
        """设置分页参数"""
        self._offset = offset
        self._limit = limit
        return self

    def order_by(self, *fields) -> 'PaginatedQueryBuilder':
        """设置排序字段"""
        for field in fields:
            if isinstance(field, str):
                if hasattr(self.model_class, field):
                    self._order_by.append(getattr(self.model_class, field))
            else:
                self._order_by.append(field)
        return self

    def build_paginated(self, base_query: Select) -> Select:
        """构建分页查询"""
        query = self.build(base_query)

        # 应用排序
        if self._order_by:
            query = query.order_by(*self._order_by)

        # 应用分页
        if self._limit:
            query = query.limit(self._limit).offset(self._offset)

        return query


# ==================== 用户模块查询构建器工厂 ====================
def create_user_query_builder() -> PaginatedQueryBuilder:
    """创建用户模块的查询构建器"""
    from app.models import SysUser

    builder = PaginatedQueryBuilder(SysUser)

    # 自动注册字段策略
    builder.auto_register_field_strategies({
        "username": {"allow_equal": True, "allow_like": True},
        "nickname": {"allow_equal": True, "allow_like": True},
        "email": {"allow_equal": True, "allow_like": True},
        "mobile": {"allow_equal": True, "allow_like": True},
        "status": {"allow_equal": True, "allow_range": True},
        "gender": {"allow_equal": True, "allow_range": True},
        "dept_id": {"allow_equal": True, "allow_in": True},  # 新增dept_id字段
    })

    # 注册复杂策略
    builder.register_strategy(
        "keywords",
        MultiFieldKeywordFilter([
            SysUser.username,
            SysUser.nickname,
            # SysUser.email,
            SysUser.mobile
        ])
    )

    builder.register_strategy(
        "create_time_range",
        DateTimeRangeFilter(SysUser.create_time)
    )

    builder.register_strategy(
        "status__in",
        InFilter(SysUser.status)
    )

    # 注册部门IN查询策略
    builder.register_strategy(
        "dept_id__in",
        InFilter(SysUser.dept_id)
    )

    # 默认排序
    builder.order_by(SysUser.create_time.desc())

    return builder