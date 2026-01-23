"""
数据字典项模型
backend/app/models/sys_dict_item.py
"""
from sqlalchemy import Column, String, SmallInteger, Integer, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, uuid_pk_column


class SysDictItem(Base):
    __tablename__ = 'sys_dict_item'
    __table_args__ = {'comment': '数据字典项表'}

    # 使用UUID主键
    id = uuid_pk_column()

    # 关联字典编码（注意：这里使用dict_code作为关联，不是外键约束）
    dict_code = Column(String(50), nullable=True, comment='关联字典编码，与sys_dict表中的dict_code对应')

    # 字典项内容
    value = Column(String(50), nullable=True, comment='字典项值')
    label = Column(String(100), nullable=True, comment='字典项标签')
    tag_type = Column(String(50), nullable=True, comment='标签类型，用于前端样式展示（如success、warning等）')
    status = Column(SmallInteger, default=0, comment='状态（1-正常，0-禁用）')
    sort = Column(Integer, default=0, comment='排序')
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

    def __repr__(self):
        return f"<SysDictItem(id={self.id}, dict_code={self.dict_code}, label={self.label})>"