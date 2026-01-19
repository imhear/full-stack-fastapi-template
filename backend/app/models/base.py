"""
基础模型文件，解决循环依赖问题
backend/app/db/base.py
"""
from sqlalchemy.ext.declarative import declarative_base

# 创建DeclarativeBase实例
Base = declarative_base()

# 导出Base用于其他模型继承
__all__ = ['Base']