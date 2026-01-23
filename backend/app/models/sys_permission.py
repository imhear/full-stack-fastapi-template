"""
系统权限模型
backend/app/models/sys_permission.py
上次更新：2026/1/22
"""
from sqlalchemy import Column, String, SmallInteger, DateTime, ForeignKey, Table, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, uuid_pk_column


class SysPermission(Base):
    __tablename__ = "sys_permission"
    __table_args__ = {'comment': '系统权限表'}

    # 使用UUID主键
    id = uuid_pk_column()
    name = Column(String(64), nullable=False, unique=True, comment='权限名称')
    code = Column(String(32), nullable=False, unique=True, comment='权限编码')
    sort = Column(SmallInteger, default=0, comment='显示顺序')
    status = Column(SmallInteger, default=1, comment='权限状态(1-正常 0-停用)')
    data_scope = Column(SmallInteger, nullable=True, comment='数据权限(1-所有数据 2-部门及子部门数据 3-本部门数据 4-本人数据)')

    # 审计字段
    create_by = Column(UUID(as_uuid=True), nullable=True, comment='创建人 ID')
    create_time = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    update_by = Column(UUID(as_uuid=True), nullable=True, comment='更新人ID')
    update_time = Column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP'),
        comment='更新时间'
    )
    is_deleted = Column(SmallInteger, default=0, comment='逻辑删除标识(0-未删除 1-已删除)')

    # 关系定义
    roles = relationship("SysRole", secondary="sys_role_permission", back_populates="permissions")

    def __repr__(self):
        return f"<SysPermission(id={self.id}, name={self.name}, code={self.code})>"
