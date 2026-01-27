"""
数据字典字段映射器
backend/app/services/mappers/dict_mapper.py
"""
from typing import Dict, Any, List
from app.models import SysDict, SysDictItem
from app.utils.field_mapper import FieldMapper


class DictFieldMapper:
    """
    数据字典字段映射器
    负责数据字典相关的数据结构转换
    """

    def __init__(self):
        # 基础字段映射配置
        self._field_mapper = FieldMapper({
            # 字典类型字段映射
            'id': 'dictId',
            'dict_code': 'dictCode',
            'create_time': 'createTime',
            'update_time': 'updateTime',

            # 字典项字段映射
            'tag_type': 'tagType',
        })

    # ==================== 字典类型转换方法 ====================

    def to_dict_type_frontend(self, dict_type: SysDict) -> Dict[str, Any]:
        """
        转换为前端字典类型格式

        Args:
            dict_type: SysDict ORM对象

        Returns:
            前端格式的字典类型字典
        """
        base_data = {
            'id': str(dict_type.id) if dict_type.id else None,
            'dict_code': dict_type.dict_code,
            'name': dict_type.name,
            'status': dict_type.status,
            'remark': dict_type.remark,
            'create_time': dict_type.create_time,
            'update_time': dict_type.update_time,
        }

        # 应用字段映射
        result = self._field_mapper.backend_to_frontend(base_data)

        # 清理None值
        return {k: v for k, v in result.items() if v is not None}

    def to_dict_types_list(self, dict_types: List[SysDict]) -> List[Dict[str, Any]]:
        """
        批量转换为字典类型列表格式

        Args:
            dict_types: SysDict ORM对象列表

        Returns:
            字典类型列表格式的字典列表
        """
        return [self.to_dict_type_frontend(dict_type) for dict_type in dict_types]

    # ==================== 字典项转换方法 ====================

    def to_dict_item_frontend(self, dict_item: SysDictItem) -> Dict[str, Any]:
        """
        转换为前端字典项格式

        Args:
            dict_item: SysDictItem ORM对象

        Returns:
            前端格式的字典项字典
        """
        base_data = {
            'id': str(dict_item.id) if dict_item.id else None,
            'dict_code': dict_item.dict_code,
            'value': dict_item.value,
            'label': dict_item.label,
            'tag_type': dict_item.tag_type,
            'status': dict_item.status,
            'sort': dict_item.sort,
            'remark': dict_item.remark,
            'create_time': dict_item.create_time,
            'update_time': dict_item.update_time,
        }

        # 应用字段映射
        result = self._field_mapper.backend_to_frontend(base_data)

        # 清理None值
        return {k: v for k, v in result.items() if v is not None}

    def to_dict_items_list(self, dict_items: List[SysDictItem]) -> List[Dict[str, Any]]:
        """
        批量转换为字典项列表格式

        Args:
            dict_items: SysDictItem ORM对象列表

        Returns:
            字典项列表格式的字典列表
        """
        return [self.to_dict_item_frontend(dict_item) for dict_item in dict_items]

    def to_dict_item_options(self, dict_items: List[SysDictItem]) -> List[Dict[str, Any]]:
        """
        转换为字典项选项格式（用于前端下拉框）

        Args:
            dict_items: SysDictItem ORM对象列表

        Returns:
            选项格式的字典列表
        """
        options = []
        for dict_item in dict_items:
            option = {
                'value': dict_item.value,
                'label': dict_item.label,
                'tagType': dict_item.tag_type,
            }
            # 清理None值
            options.append({k: v for k, v in option.items() if v is not None})
        return options


# 全局字典映射器实例
dict_mapper = DictFieldMapper()