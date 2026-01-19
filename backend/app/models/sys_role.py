"""
角色模块数据库模型文件
backend/app/models/sys_role.py
上次更新：2026/1/19
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+内置，无需安装
import uuid

from app.models.base import Base


class SysRole(Base):
    __tablename__ = "sys_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), unique=True, index=True, nullable=False)
    code = Column(String(64), unique=True, index=True, nullable=False)  # 角色代码，如：admin, user, guest
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # 是否为系统内置角色
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("UTC")))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("UTC")),
        onupdate=lambda: datetime.now(ZoneInfo("UTC"))
    )
    # 关系定义（使用字符串引用来避免循环导入）
    users = relationship("SysUser", secondary="sys_user_roles", back_populates="roles")
    permissions = relationship("SysPermission", secondary="sys_role_permissions", back_populates="roles")

    def __repr__(self):
        return f"<SysRole(id={self.id}, name={self.name})>"


# 角色权限关联表（多对多）
sys_role_permissions = Table(
    'sys_role_permissions', Base.metadata,
    Column('role_id', String(36), ForeignKey('sys_roles.id'), primary_key=True),
    Column('permission_id', String(36), ForeignKey('sys_permissions.id'), primary_key=True),
    Column('created_at', DateTime, default=lambda: datetime.now(ZoneInfo("UTC")))
)