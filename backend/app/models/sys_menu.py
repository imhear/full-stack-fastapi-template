"""
系统菜单模型
backend/app/models/sys_menu.py
"""
from sqlalchemy import Column, String, SmallInteger, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, uuid_pk_column


class SysMenu(Base):
    __tablename__ = 'sys_menu'
    __table_args__ = {'comment': '系统菜单表'}

    # 使用UUID主键
    id = uuid_pk_column()

    parent_id = Column(UUID(as_uuid=True),nullable=True,default=None,comment='父菜单ID（NULL表示顶级菜单）')
    tree_path = Column(String(255), nullable=True, comment='父节点ID路径')
    name = Column(String(64), nullable=False, comment='菜单名称')
    type = Column(String(1), nullable=False, comment='菜单类型（C-目录 M-菜单 B-按钮）')
    route_name = Column(String(255), nullable=True, comment='路由名称（Vue Router 中用于命名路由）')
    route_path = Column(String(128), nullable=True, comment='路由路径（Vue Router 中定义的 URL 路径）')
    component = Column(String(128), nullable=True, comment='组件路径（组件页面完整路径，相对于 src/views/，缺省后缀 .vue）')
    perm = Column(String(128), nullable=True, comment='【按钮】权限标识')
    always_show = Column(SmallInteger, default=0, comment='【目录】只有一个子路由是否始终显示（1-是 0-否）')
    keep_alive = Column(SmallInteger, default=0, comment='【菜单】是否开启页面缓存（1-是 0-否）')
    visible = Column(SmallInteger, default=1, comment='显示状态（1-显示 0-隐藏）')
    sort = Column(SmallInteger, default=0, comment='排序')
    icon = Column(String(64), nullable=True, comment='菜单图标')
    redirect = Column(String(128), nullable=True, comment='跳转路径')
    params = Column(String(255), nullable=True, comment='路由参数')

    # 时间戳（不设默认值，由数据库处理）
    create_time = Column(DateTime, nullable=True, comment='创建时间')
    update_time = Column(DateTime, nullable=True, comment='更新时间')

    # 与角色的多对多关系
    roles = relationship('SysRole', secondary='sys_role_menu', back_populates='menus')

    def __repr__(self):
        return f"<SysMenu(id={self.id}, name={self.name}, type={self.type})>"