"""
backend/app/services/mappers/constants.py
用户字段映射器常量定义
"""


# 格式类型枚举
class FormatType:
    """格式类型枚举"""
    ME_RESPONSE = "me_response"
    PROFILE = "profile"
    LIST_ITEM = "list_item"
    DETAIL = "detail"
    FORM = "form"


# 字段映射配置
FIELD_MAPPINGS = {
    # 用户标识
    'id': 'id',

    # 时间字段
    'create_time': 'createTime',
    'update_time': 'updateTime',
    'last_login': 'lastLogin',

    # 组织字段
    'dept_id': 'deptId',
    'dept_name': 'deptName',

    # 个人信息
    'status': 'status',
    'role_ids': 'roleIds',
}

# 调试配置
DEBUG_CONFIG = {
    'enabled': False,  # 生产环境应设置为False
    'log_level': 'DEBUG'
}