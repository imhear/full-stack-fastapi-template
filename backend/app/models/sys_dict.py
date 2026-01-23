"""
数据字典类型模型
backend/app/models/sys_dict.py
"""
from sqlalchemy import Column, String, SmallInteger, DateTime, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, uuid_pk_column


class SysDict(Base):
    __tablename__ = 'sys_dict'
    __table_args__ = {'comment': '数据字典类型表'}

    # 使用UUID主键
    id = uuid_pk_column()
    dict_code = Column(String(50), nullable=True, comment='类型编码')
    name = Column(String(50), nullable=True, comment='类型名称')
    status = Column(SmallInteger, default=0, comment='状态(0:正常;1:禁用)')
    remark = Column(String(255), nullable=True, comment='备注')

    # 审计字段
    create_time = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    create_by = Column(UUID(as_uuid=True), nullable=True, comment='创建人ID')
    update_time = Column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP'),
        comment='更新时间'
    )
    update_by = Column(UUID(as_uuid=True), nullable=True, comment='修改人ID')
    is_deleted = Column(SmallInteger, default=0, comment='是否删除(1-删除，0-未删除)')

    def __repr__(self):
        return f"<SysDict(id={self.id}, dict_code={self.dict_code}, name={self.name})>"