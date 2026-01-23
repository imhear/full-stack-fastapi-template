"""
部门管理模型
backend/app/models/sys_dept.py
"""
from sqlalchemy import Column, String, SmallInteger, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base, uuid_pk_column


class SysDept(Base):
    __tablename__ = 'sys_dept'
    __table_args__ = {'comment': '部门管理表'}

    # 使用UUID主键
    id = uuid_pk_column()
    name = Column(String(100), nullable=False, comment='部门名称')
    code = Column(String(100), nullable=False, unique=True, comment='部门编号')

    # 自关联外键，使用PostgreSQL的UUID类型
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sys_dept.id', ondelete='SET NULL'),
        nullable=True,
        comment='父节点id'
    )

    tree_path = Column(String(255), nullable=False, comment='父节点id路径')
    sort = Column(SmallInteger, default=0, comment='显示顺序')
    status = Column(SmallInteger, default=1, comment='状态(1-正常 0-禁用)')

    # 关联字段使用UUID
    create_by = Column(UUID(as_uuid=True), nullable=True, comment='创建人ID')
    create_time = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    update_by = Column(UUID(as_uuid=True), nullable=True, comment='修改人ID')
    update_time = Column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP'),
        comment='更新时间'
    )
    is_deleted = Column(SmallInteger, default=0, comment='逻辑删除标识(1-已删除 0-未删除)')

    # 自关联关系
    parent = relationship('SysDept', remote_side=[id], backref='children')

    # 与用户的关联（在sys_user模型中定义）

    def __repr__(self):
        return f"<SysDept(id={self.id}, name={self.name}, code={self.code})>"