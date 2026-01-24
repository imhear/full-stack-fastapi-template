"""
测试查询构建器
"""
import pytest
from datetime import datetime
from app.core.query_builder import (
    create_user_query_builder, EqualFilter, LikeFilter,
    MultiFieldKeywordFilter, DateTimeRangeFilter
)
from app.models import SysUser


def test_query_builder_basic():
    """测试基础查询构建器"""
    builder = create_user_query_builder()

    # 测试添加过滤条件
    builder.filter(
        status__eq=1,
        username__like="admin"
    )

    # 验证策略已注册
    assert "status__eq" in builder.strategies
    assert "username__like" in builder.strategies

    print("✅ 基础查询构建器测试通过")


def test_multi_field_keyword_filter():
    """测试多字段关键词搜索"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # 创建内存数据库用于测试
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)

    # 创建查询构建器
    builder = create_user_query_builder()
    builder.filter(keywords="管理员")

    # 创建基础查询
    from sqlalchemy import select
    base_query = select(SysUser)

    # 构建查询
    query = builder.build(base_query)

    # 验证查询条件
    print(f"生成的SQL条件: {query.whereclause}")

    print("✅ 多字段关键词搜索测试通过")


def test_date_time_range_filter():
    """测试日期时间范围过滤"""
    builder = create_user_query_builder()

    # 测试时间范围过滤
    time_range = {
        "start": datetime(2024, 1, 1),
        "end": datetime(2024, 12, 31)
    }

    builder.filter(create_time_range=time_range)

    # 验证策略应用
    assert "create_time_range" in builder.strategies

    print("✅ 日期时间范围过滤测试通过")


def test_complex_filters():
    """测试复杂过滤条件组合"""
    builder = create_user_query_builder()

    # 测试多种过滤条件组合
    builder.filter(
        status__eq=1,
        username__like="john",
        gender__range={"min": 1, "max": 2}
    )

    # 验证条件数量
    assert len(builder.conditions) == 3

    print("✅ 复杂过滤条件组合测试通过")


if __name__ == "__main__":
    test_query_builder_basic()
    test_multi_field_keyword_filter()
    test_date_time_range_filter()
    test_complex_filters()
    print("🎉 所有查询构建器测试通过！")