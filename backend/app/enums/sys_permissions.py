# !/usr/bin/env python3
"""
权限枚举文件
backend/app/enums/permissions.py
# 上次更新：2025/12/10（第28轮：增量新增文档更新/删除权限）
# 原上次更新：2025/12/03（第86轮权限优化）
"""
from enum import Enum
from pathlib import Path
from datetime import datetime


class PermissionCode(Enum):
    """
    系统权限枚举类
    每个枚举值格式: (权限代码, 显示名称, 描述)
    """

    def __new__(cls, code: str, name: str, description: str):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.display_name = name
        obj.description = description
        return obj

    # 用户管理权限
    USER_READ_LIST = ("user:read:list", "查看用户列表", "允许查看系统中的用户列表")
    USER_READ = ("user:read", "查询用户详情", "需要【user:read】权限，仅超级用户可访问")
    USER_CREATE = ("user:create", "创建用户", "允许在系统中创建新用户")
    USER_UPDATE = ("user:update", "更新用户", "允许修改现有用户信息")
    USER_DELETE = ("user:delete", "删除用户", "允许从系统中删除用户")

    # 新增：用户回收站权限
    USER_RECYCLE_BIN_VIEW = ("user:recycle-bin:view", "查看回收站", "允许查看已删除的用户列表")
    USER_RECYCLE_BIN_RESTORE = ("user:recycle-bin:restore", "恢复用户", "允许恢复已删除的用户")

    # 部门管理权限
    DEPT_READ = ("dept:read", "查询部门详情", "需要【dept:read】权限，仅超级用户可访问")
    DEPT_CREATE = ("dept:create", "创建部门", "允许在系统中创建新部门")
    DEPT_UPDATE = ("dept:update", "更新部门", "允许修改现有部门信息")
    DEPT_DELETE = ("dept:delete", "删除部门", "允许从系统中删除部门")

    # 数据字典权限
    SYSTEM_DICT_READ = ("system:dict:read", "查看数据字典", "允许查看数据字典")
    SYSTEM_DICT_CREATE = ("system:dict:create", "创建数据字典", "允许创建数据字典")
    SYSTEM_DICT_UPDATE = ("system:dict:update", "更新数据字典", "允许更新数据字典")
    SYSTEM_DICT_DELETE = ("system:dict:delete", "删除数据字典", "允许从删除数据字典")

    # 角色管理权限
    ROLE_ASSIGN = ("role:assign", "角色分配", "为用户分配角色")
    ROLE_MANAGE = ("role:manage", "角色管理", "管理角色配置")

    # 手册文档模块权限（第86轮新增，专属接口权限）
    MANUAL_DOC_CATEGORY_VIEW = ("manual:doc:category:view", "文档分类查看", "允许查看手册文档分类列表")
    MANUAL_DOC_LIST_VIEW = ("manual:doc:list:view", "文档列表查看", "允许查看手册文档列表（支持分类筛选）")
    # 第44轮新增：文档创建/详情权限（修复启动AttributeError报错）
    MANUAL_DOC_CREATE = ("manual:doc:create", "文档创建", "允许创建新的手册文档（含文件存储）")
    MANUAL_DOC_DETAIL_VIEW = ("manual:doc:detail:view", "文档详情查看", "允许查看指定ID的手册文档详情（含内容）")
    # 第28轮新增：文档更新/删除权限（最小化增量修改，支撑更新/删除接口）
    MANUAL_DOC_UPDATE = ("manual:doc:update", "文档更新/编辑", "允许更新/编辑指定ID的手册文档（含内容覆盖）")
    MANUAL_DOC_DELETE = ("manual:doc:delete", "文档删除", "允许软删除指定ID的手册文档（仅更新is_deleted=1）")

    @classmethod
    def get_all(cls):
        """获取所有权限枚举实例"""
        return list(cls)


def generate_markdown_docs():
    """生成带时间戳的Markdown格式权限文档"""
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    markdown = f"# PermissionCode 权限文档\n\n"
    markdown += f"> **文档生成时间**: {current_time}\n\n"
    markdown += "| 权限代码 | 显示名称 | 描述 |\n"
    markdown += "|----------|----------|------|\n"

    for perm in PermissionCode.get_all():
        markdown += f"| `{perm.value}` | {perm.display_name} | {perm.description} |\n"

    return markdown


def save_to_file(content: str, filepath: str = "permission_docs.md"):
    """将文档保存到指定文件"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"权限文档已生成到: {path.absolute()}")

def save_permission_docs():
    """保存权限文档到文件"""
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    filepath = docs_dir / "permission_docs.md"
    content = generate_markdown_docs()
    filepath.write_text(content, encoding="utf-8")
    return filepath

if __name__ == "__main__":
    docs = generate_markdown_docs()
    save_to_file(docs)

# 溯源记录（按开发手册分组）
## 手册9《MVP后端开发手册（三）：文档创建与详情接口》
# 86轮溯源：新增手册文档分类/列表权限（MANUAL_DOC_CATEGORY_VIEW/MANUAL_DOC_LIST_VIEW），优化权限枚举结构，补充文档生成逻辑
# 44轮溯源：补充MANUAL_DOC_CREATE/MANUAL_DOC_DETAIL_VIEW权限值，修复manual_doc_endpoint.py启动AttributeError报错，保留所有原有代码逻辑
## 手册4《MVP后端开发手册（四）：文档更新与删除接口》
# 28轮溯源：最小化增量新增MANUAL_DOC_UPDATE/MANUAL_DOC_DELETE权限枚举值，无其他代码/逻辑修改，确保权限同步脚本正常执行
# 29轮溯源：仅修正头部注释格式（上次更新/原上次更新分行）、重构溯源记录为手册分组格式，无代码逻辑/权限枚举修改
# 30轮溯源：补充doc_update_schema.py/doc_delete_schema.py全量源码，解决导入报错，无代码逻辑修改
# 31轮溯源：仅缩减沟通记录为最新5轮，无任何代码逻辑/格式修改
# 32轮溯源：仅修正头部注释触发逻辑（仅代码逻辑修改更新“上次更新”），无代码逻辑修改
# 33轮溯源：仅保留上述修正，无代码逻辑/内容修改，全量保留原有代码
# 34轮溯源：仅同步注释规范校验，无代码逻辑/内容修改，全量保留原有代码
# 35轮溯源：无任何修改，全量保留原有代码/注释/溯源
# 36轮溯源：无任何修改，全量保留原有代码/注释/溯源
# 37轮溯源：无任何修改，全量保留原有代码/注释/溯源