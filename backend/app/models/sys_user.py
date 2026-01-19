"""
用户模块数据库模型文件
backend/app/models/sys_user.py
上次更新：2026/1/19
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+内置，无需安装
import uuid

from app.models.base import Base


class SysUser(Base):
    __tablename__ = "sys_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(64))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    # 关键修改：使用TIMESTAMPTZ（PostgreSQL专用）
    # SQLAlchemy会自动映射为带时区的时间类型
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("UTC")))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("UTC")),
        onupdate=lambda: datetime.now(ZoneInfo("UTC"))
    )

    # 使用字符串引用来避免循环导入
    roles = relationship("SysRole", secondary="sys_user_roles", back_populates="users")


# 用户角色关联表（多对多）
sys_user_roles = Table(
    'sys_user_roles', Base.metadata,
    Column('user_id', String(36), ForeignKey('sys_users.id'), primary_key=True),
    Column('role_id', String(36), ForeignKey('sys_roles.id'), primary_key=True),
    Column('created_at', DateTime, default=lambda: datetime.now(ZoneInfo("UTC")))
)

# wt@wt.com
# $2b$12$mfSxUNsgP2CzDWBIvv1TSeh9E6twy/NZpTgkR7n783owKulVWsKYq