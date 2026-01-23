"""
模型统一导出入口
作用：
1. 集中管理所有模型导入，避免散落在业务代码中的重复导入
2. 按SQLAlchemy依赖顺序导入，解决循环依赖问题
3. 统一导出所有模型，简化业务层导入（如：from app.models import SysUser）

遵循原则：
- import顺序：先导入"被依赖的底层模型"，后导入"依赖它的上层模型"
- __all__顺序：与import顺序保持一致，提升可维护性
- 仅导出需要对外暴露的模型/表，内部实现不暴露

backend/app/models/__init__.py
create_by：wutao@wt.com
create_time：2026/1/22
update_by wutao@wt.com
update_time：2026/1/20
"""
import sys
import os

# 将项目根目录加入Python路径
CURRENT_FILE_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE_PATH)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 1. 基础依赖：先导入所有模型的基类
try:
    from app.models.base import Base, uuid_pk_column
except ImportError as e:
    raise ImportError(f"导入Base基类失败: {e}")

# 2. 核心模型：按"被依赖→依赖"顺序导入（底层→上层）
try:
    # 2.1 基础数据模型（无外键依赖）
    from app.models.sys_dept import SysDept
    from app.models.sys_dict import SysDict
    from app.models.sys_dict_item import SysDictItem
    from app.models.sys_menu import SysMenu
    from app.models.sys_permission import SysPermission
    from app.models.sys_role import SysRole, sys_role_menu, sys_role_permission
    # from app.models.sys_config import SysConfig
    # from app.models.sys_notice import SysNotice

    # 2.2 依赖其他模型的模型
    from app.models.sys_user import SysUser, sys_user_role
    # from app.models.sys_user_notice import SysUserNotice
    # from app.models.sys_log import SysLog
    # from app.models.gen_table import GenTable
    # from app.models.gen_table_column import GenTableColumn
    # from app.models.ai_assistant_record import AiAssistantRecord

except ImportError as e:
    raise ImportError(f"导入模型失败: {e}")


# 3. 统一导出：与导入顺序严格一致
__all__ = [
    # 基础类
    'Base', 'uuid_pk_column',

    # 核心模型（按依赖顺序）
    'SysDept',
    'SysDict',
    'SysDictItem',
    'SysMenu',
    'SysRole',
    'sys_role_menu',
    # 'SysConfig',
    # 'SysNotice',

    # 依赖其他模型的模型
    'SysUser',
    'sys_user_role',
    # 'SysUserNotice',
    # 'SysLog',
    # 'GenTable',
    # 'GenTableColumn',
    # 'AiAssistantRecord',
]


# 4. 开发环境模型校验
def validate_models() -> None:
    """验证所有模型类是否正确继承Base基类"""
    module_globals = globals()

    for model_name in __all__:
        if model_name in ['Base', 'uuid_pk_column']:
            continue

        if model_name not in module_globals:
            raise RuntimeError(f"导出列表中的 {model_name} 未在模块中定义")

        model = module_globals[model_name]

        # 跳过关联表（Table实例）和函数
        if isinstance(model, type) and hasattr(model, '__tablename__'):
            if not issubclass(model, Base):
                raise RuntimeError(f"模型 {model_name} 未正确继承Base基类！")


# 仅在直接运行该文件时执行校验
if __name__ == "__main__":
    try:
        validate_models()
        print("✅ 所有模型校验通过，依赖顺序正确")
    except RuntimeError as e:
        print(f"❌ 模型校验失败：{e}")
        raise
    except Exception as e:
        print(f"❌ 校验过程中出现未知错误：{e}")
        raise

"""
11c136ad-a815-4dee-8d23-4bf6d7948920
wt@wt.com
$2b$12$mfSxUNsgP2CzDWBIvv1TSeh9E6twy/NZpTgkR7n783owKulVWsKYq
2026-01-21 09:14:51.889115+08


# 连接到PostgreSQL，删除旧数据库
wutao@wutaodeMacBook-Pro vue3-element-template % psql -d postgres -c "DROP DATABASE IF EXISTS admin_panel_2026;"
DROP DATABASE

 使用 template0 模板创建数据库（能避免兼容性问题）
wutao@wutaodeMacBook-Pro vue3-element-template % psql -d postgres -c "CREATE DATABASE admin_panel_2026 ENCODING 'UTF8' TEMPLATE template0;"
CREATE DATABASE
wutao@wutaodeMacBook-Pro vue3-element-template % 

# 验证创建成功
wutao@wutaodeMacBook-Pro vue3-element-template % psql -d admin_panel_2026 -c "SELECT current_database(), current_user;"
 current_database | current_user 
------------------+--------------
 admin_panel_2026 | wutao
(1 row)

wutao@wutaodeMacBook-Pro vue3-element-template % 
"""