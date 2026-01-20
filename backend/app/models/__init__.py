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
上次更新：2026/1/20
"""
import sys
import os

# 关键修复：将项目根目录加入Python路径，确保直接运行该文件时能找到app包
# 获取当前文件（__init__.py）的绝对路径
CURRENT_FILE_PATH = os.path.abspath(__file__)
# 向上找到项目根目录（backend）
# 路径层级：backend/app/models/__init__.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE_PATH)))
# 将项目根目录加入sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 1. 基础依赖：先导入所有模型的基类（无任何依赖）
try:
    from app.models.base import Base
except ImportError as e:
    raise ImportError(f"导入Base基类失败，请检查路径是否正确：{e}")

# 2. 核心模型：按"被依赖→依赖"顺序导入（底层→上层）
try:
    # 2.1 权限模型：无前置依赖（最底层）
    from app.models.sys_permission import SysPermission
    # 2.2 角色模型：依赖权限模型
    from app.models.sys_role import SysRole, sys_role_permissions
    # 2.3 用户模型：依赖角色模型（最上层）
    from app.models.sys_user import SysUser, sys_user_roles
except ImportError as e:
    raise ImportError(f"导入模型失败，请检查模型文件是否存在或路径正确：{e}")

# 3. 统一导出：与导入顺序严格一致，便于维护和排查依赖问题
#    （__all__仅控制"from app.models import *"的导出范围，不影响功能执行）
__all__ = [
    # 基础类
    'Base',
    # 核心模型（按导入顺序）
    'SysPermission',
    'SysRole',
    'SysUser',
    # 中间表（按所属模型顺序）
    'sys_role_permissions',
    'sys_user_roles',
]

# 4. 安全校验：开发环境模型校验（生产环境不执行）
def validate_models() -> None:
    """
    验证所有模型类是否正确继承Base基类，避免开发时的低级错误
    说明：
    - 跳过Base本身和中间表（Table对象），仅校验模型类
    - 若模型未正确继承Base，会抛出RuntimeError，提前暴露问题
    """
    # 改用globals()获取模块级别的全局变量（修复KeyError核心问题）
    module_globals = globals()

    for model_name in __all__:
        # 跳过Base基类本身
        if model_name == 'Base':
            continue

        # 检查变量是否存在，避免KeyError
        if model_name not in module_globals:
            raise RuntimeError(f"导出列表中的 {model_name} 未在模块中定义，请检查导入语句是否正确")

        # 获取导出的模型/表对象
        model = module_globals[model_name]

        # 跳过多对多中间表（Table实例），仅校验模型类
        # 中间表是Table对象，不是类，无需继承Base
        if isinstance(model, type):  # 仅处理类对象（模型类）
            if not issubclass(model, Base):
                raise RuntimeError(f"模型 {model_name} 未正确继承Base基类！所有业务模型必须继承Base")

# 仅在直接运行该文件时执行校验（仅开发环境执行校验）
# 生产环境中，该文件会被作为模块导入（`import app.models`），此时 `__name__ != "__main__"`，校验逻辑不会执行
# 执行命令：((.venv) ) wutaodeMacBook-Pro:backend wutao$ python app/models/__init__.py
if __name__ == "__main__":
    try:
        validate_models()
        print("✅ 所有模型校验通过，依赖顺序正确，且均已正确继承Base基类")
    except RuntimeError as e:
        print(f"❌ 模型校验失败：{e}")
        raise  # 抛出异常，让调试更直观
    except Exception as e:
        print(f"❌ 校验过程中出现未知错误：{e}")
        raise