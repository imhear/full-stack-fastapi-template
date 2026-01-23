"""
SQLAlchemy Declarative Base
backend/app/models/base.py
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

# 创建DeclarativeBase实例
Base = declarative_base()

# PostgreSQL UUID类型配置
def uuid_pk_column():
    """生成UUID主键列的辅助函数"""
    from sqlalchemy import Column
    return Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )

__all__ = ['Base', 'uuid_pk_column']