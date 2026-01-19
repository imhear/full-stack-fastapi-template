"""
权限模块数据库模型文件
backend/app/models/sys_permission.py
上次更新：2026/1/19
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+内置，无需安装
import uuid

from app.models.base import Base


class SysPermission(Base):
    __tablename__ = "sys_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, index=True, nullable=False)  # 权限代码，如：user:create, post:delete
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(16), default="general")  # 权限分类，如：user_management, content_management
    module = Column(String(16), nullable=True)  # 所属模块
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # 是否为系统内置权限
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("UTC")))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("UTC")),
        onupdate=lambda: datetime.now(ZoneInfo("UTC"))
    )
    # 关系定义
    roles = relationship("SysRole", secondary="sys_role_permissions", back_populates="permissions")

    def __repr__(self):
        return f"<SysPermission(id={self.id}, code={self.code})>"