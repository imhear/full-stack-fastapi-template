"""
字段映射工具 - 处理前后端字段名转换
backend/app/utils/field_mapper.py
行业最佳实践：在服务层进行显式字段映射，保持数据库命名规范，提供前端友好格式

参考：Shopify、AWS、GitHub等公司的生产实践
"""
from typing import Dict, Any, List, Union, Optional
import inflection
import re
from enum import Enum


class CaseStyle(Enum):
    """字段命名风格枚举"""
    SNAKE_CASE = "snake_case"  # 数据库和后端标准
    CAMEL_CASE = "camelCase"  # 前端标准
    PASCAL_CASE = "PascalCase"  # 类名标准


class FieldMapper:
    """
    字段映射器 - 生产级实现

    核心原则：
    1. 数据库层：保持snake_case（行业标准）
    2. API层：接收和返回camelCase（前端标准）
    3. 转换逻辑：在服务层显式处理（可维护性）
    4. 映射规则：支持自定义覆盖（灵活性）

    设计模式：策略模式 + 装饰器模式
    """

    # 常用字段映射规则（可根据项目扩展）
    COMMON_MAPPINGS = {
        # 通用字段
        'id': 'id',  # 保持原样，特殊情况单独处理
        'created_time': 'createTime',
        'updated_time': 'updateTime',
        'is_deleted': 'isDeleted',

        # 角色相关
        'role_id': 'roleId',
        'role_name': 'roleName',
        'role_code': 'roleCode',
        'is_system': 'isSystem',
    }

    def __init__(self, custom_mappings: Optional[Dict[str, str]] = None):
        """
        初始化字段映射器

        Args:
            custom_mappings: 自定义映射规则，优先级高于默认规则
        """
        # 删除调试代码，保持干净
        self._mappings = {**self.COMMON_MAPPINGS}
        if custom_mappings:
            self._mappings.update(custom_mappings)

        # 生成反向映射（用于前端到后端的转换）
        self._reverse_mappings = {v: k for k, v in self._mappings.items()}

    def to_snake_case(self, text: str) -> str:
        """
        camelCase/PascalCase 转换为 snake_case

        算法复杂度: O(n)
        内存复杂度: O(n)

        Args:
            text: 驼峰命名字符串

        Returns:
            snake_case字符串
        """
        if not text:
            return text

        # 处理连续大写（如HTMLParser -> html_parser）
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)

        # 处理单个大写字母（如userId -> user_id）
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)

        return s2.lower()

    def to_camel_case(self, text: str, first_upper: bool = False) -> str:
        """
        snake_case 转换为 camelCase

        Args:
            text: 下划线命名字符串
            first_upper: 是否首字母大写（PascalCase）

        Returns:
            camelCase字符串
        """
        if not text:
            return text

        # 使用inflection库，更成熟稳定
        if first_upper:
            return inflection.camelize(text, uppercase_first_letter=True)
        else:
            return inflection.camelize(text, uppercase_first_letter=False)

    def _convert_keys(
            self,
            data: Any,
            conversion_func: callable,
            mapping_dict: Dict[str, str],
            depth: int = 0,
            max_depth: int = 10
    ) -> Any:
        """
        递归转换字典键名

        安全机制：
        1. 防止无限递归（max_depth限制）
        2. 处理循环引用
        3. 保持原始数据类型

        Args:
            data: 要转换的数据
            conversion_func: 键名转换函数
            mapping_dict: 映射字典（现在仅用于递归传递，不再用于键名转换）
            depth: 当前递归深度
            max_depth: 最大递归深度

        Returns:
            转换后的数据
        """
        # 安全机制：防止无限递归
        if depth > max_depth:
            raise RecursionError(f"Maximum recursion depth ({max_depth}) exceeded")

        # 处理字典类型
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # 修复关键点：直接使用 conversion_func 转换键名，不再通过 mapping_dict.get
                # 原逻辑：mapped_key = mapping_dict.get(key, key)
                #          new_key = conversion_func(mapped_key)
                # 新逻辑：直接使用 key 调用 conversion_func
                new_key = conversion_func(key)
                # 递归处理值
                result[new_key] = self._convert_keys(
                    value, conversion_func, mapping_dict, depth + 1, max_depth
                )
            return result

        # 处理列表类型
        elif isinstance(data, list):
            return [
                self._convert_keys(item, conversion_func, mapping_dict, depth + 1, max_depth)
                for item in data
            ]

        # 处理其他类型（直接返回）
        else:
            return data

    def backend_to_frontend(self, data: Union[Dict, List]) -> Union[Dict, List]:
        """
        后端数据转换为前端格式（snake_case -> camelCase）

        使用场景：从数据库查询数据后，返回给前端之前

        Args:
            data: 后端格式的数据（snake_case）

        Returns:
            前端格式的数据（camelCase）
        """
        def conversion_func(key: str) -> str:
            # 修复关键点：使用正向映射规则（后端字段名 -> 前端字段名）
            # 原逻辑：if key in self._reverse_mappings:
            #              return self._reverse_mappings[key]
            # 新逻辑：if key in self._mappings:
            #              return self._mappings[key]

            if key in self._mappings:
                return self._mappings[key]
            # 否则使用默认转换
            return self.to_camel_case(key)

        # 修复关键点：传入 self._mappings 作为 mapping_dict
        # 虽然 mapping_dict 在 _convert_keys 中不再用于键名转换，
        # 但为了保持接口一致性，仍然传入正确的映射字典
        return self._convert_keys(data, conversion_func, self._mappings)

    def frontend_to_backend(self, data: Union[Dict, List]) -> Union[Dict, List]:
        """
        前端数据转换为后端格式（camelCase -> snake_case）

        使用场景：接收前端请求数据后，保存到数据库之前

        Args:
            data: 前端格式的数据（camelCase）

        Returns:
            后端格式的数据（snake_case）
        """
        def conversion_func(key: str) -> str:
            # 修复关键点：使用反向映射规则（前端字段名 -> 后端字段名）
            if key in self._reverse_mappings:
                return self._reverse_mappings[key]
            # 否则使用默认转换
            return self.to_snake_case(key)

        # 修复关键点：传入 self._reverse_mappings 作为 mapping_dict
        return self._convert_keys(data, conversion_func, self._reverse_mappings)

    def register_mapping(self, backend_key: str, frontend_key: str) -> None:
        """
        注册自定义映射规则

        Args:
            backend_key: 后端字段名（snake_case）
            frontend_key: 前端字段名（camelCase）
        """
        self._mappings[backend_key] = frontend_key
        self._reverse_mappings[frontend_key] = backend_key

    def batch_register_mappings(self, mappings: Dict[str, str]) -> None:
        """
        批量注册映射规则

        Args:
            mappings: 映射规则字典 {backend_key: frontend_key}
        """
        for backend_key, frontend_key in mappings.items():
            self.register_mapping(backend_key, frontend_key)


# 全局实例（推荐使用）
default_mapper = FieldMapper()