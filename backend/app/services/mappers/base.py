"""
backend/app/services/mappers/base.py
映射器基类和接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol
from datetime import datetime
from app.models import SysUser


class BaseExtractor(ABC):
    """数据提取器基类"""

    @abstractmethod
    def extract(self, user: SysUser) -> Dict[str, Any]:
        """提取数据"""
        pass


class FormatStrategy(Protocol):
    """格式转换策略协议"""

    def format_name(self) -> str:
        """返回格式名称"""
        pass

    def transform(self, base_data: Dict[str, Any], user: SysUser) -> Dict[str, Any]:
        """转换数据到目标格式"""
        pass


class DataTransformer:
    """数据转换器基类"""

    def __init__(self, debug: bool = False):
        self.debug = debug

    def _log_debug(self, message: str, data: Any = None):
        """调试日志"""
        if self.debug:
            print(f"[DEBUG] {message}")
            if data:
                print(f"[DEBUG] Data: {data}")