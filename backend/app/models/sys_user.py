"""
系统用户模型
backend/app/models/sys_user.py
"""
from sqlalchemy import Column, String, SmallInteger, DateTime, ForeignKey, Table, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base, uuid_pk_column

class SysUser(Base):
    __tablename__ = 'sys_user'
    __table_args__ = {'comment': '系统用户表'}

    # 使用UUID主键
    id = uuid_pk_column()
    username = Column(String(64), unique=True, index=True, comment='用户名')
    nickname = Column(String(64), comment='昵称')
    gender = Column(SmallInteger, default=1, comment='性别(1-男 2-女 0-保密)')
    password = Column(String(100), nullable=False, comment='密码')

    # 部门ID改为UUID类型（不设置外键约束，保持与原始设计一致）
    dept_id = Column(UUID(as_uuid=True), nullable=True, comment='部门ID')

    avatar = Column(String(255), comment='用户头像')
    mobile = Column(String(20), comment='联系方式')
    status = Column(SmallInteger, default=1, comment='状态(1-正常 0-禁用)')
    email = Column(String(128), comment='用户邮箱')

    # 时间戳和审计字段
    create_time = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    create_by = Column(UUID(as_uuid=True), nullable=True, comment='创建人ID')
    update_time = Column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP'),
        comment='更新时间'
    )
    update_by = Column(UUID(as_uuid=True), nullable=True, comment='修改人ID')
    is_deleted = Column(SmallInteger, default=0, comment='逻辑删除标识(0-未删除 1-已删除)')
    openid = Column(String(28), comment='微信 openid')

    # 与角色的多对多关系
    roles = relationship('SysRole', secondary='sys_user_role', back_populates='users')

    def __repr__(self):
        return f"<SysUser(id={self.id}, username={self.username}, nickname={self.nickname})>"


# 用户角色关联表（多对多）
from sqlalchemy import Column, ForeignKey
from app.models.base import Base

sys_user_role = Table(
    'sys_user_role',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('sys_user.id'), primary_key=True, comment='用户ID'),
    Column('role_id', UUID(as_uuid=True), ForeignKey('sys_role.id'), primary_key=True, comment='角色ID'),
    comment='用户角色关联表'
)