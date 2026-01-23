"""
初始化基础数据（简化版）- 针对PostgreSQL + UUID主键
backend/app/scripts/init_data.py
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 加载.env文件
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"ℹ️ 成功加载.env文件：{env_path}")
else:
    raise FileNotFoundError("❌ 未找到.env文件")

# 导入项目核心配置
from app.core.config import settings


# 数据库会话创建
def create_async_db_session() -> sessionmaker[AsyncSession]:
    database_url = str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    async_engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )

    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return async_session_factory


# UUID映射定义
UUID_MAP: Dict[str, UUID] = {
    # 部门ID映射
    "dept_1": UUID("11111111-1111-1111-1111-111111111111"),
    "dept_2": UUID("22222222-2222-2222-2222-222222222222"),
    "dept_3": UUID("33333333-3333-3333-3333-333333333333"),

    # 角色ID映射
    "role_1": UUID("44444444-4444-4444-4444-444444444444"),
    "role_2": UUID("55555555-5555-5555-5555-555555555555"),
    "role_3": UUID("66666666-6666-6666-6666-666666666666"),

    # 用户ID映射
    "user_1": UUID("11111111-2222-3333-4444-555555555555"),
    "user_2": UUID("22222222-3333-4444-5555-666666666666"),
    "user_3": UUID("33333333-4444-5555-6666-777777777777"),
}

# 密码哈希（对应明文123456）
HASHED_PASSWORD = "$2a$10$xVWsNOhHrCxh5UbpCE7/HuJ.PAOKcYAqRxD2CO2nVnJS.IAXkr5aq"


# 初始化部门数据
async def init_sys_dept(session: AsyncSession) -> int:
    print("📁 初始化部门数据...")

    dept_data = [
        {
            "id": UUID_MAP["dept_1"],
            "name": "有来技术",
            "code": "YOULAI",
            "parent_id": None,
            "tree_path": "0",
            "sort": 1,
            "status": 1,
            "create_by": UUID_MAP["user_1"],
            "create_time": datetime.now(),
            "update_by": UUID_MAP["user_1"],
            "update_time": datetime.now(),
            "is_deleted": 0
        },
        {
            "id": UUID_MAP["dept_2"],
            "name": "研发部门",
            "code": "RD001",
            "parent_id": UUID_MAP["dept_1"],
            "tree_path": f"0,{UUID_MAP['dept_1']}",
            "sort": 1,
            "status": 1,
            "create_by": UUID_MAP["user_2"],
            "create_time": datetime.now(),
            "update_by": UUID_MAP["user_2"],
            "update_time": datetime.now(),
            "is_deleted": 0
        },
        {
            "id": UUID_MAP["dept_3"],
            "name": "测试部门",
            "code": "QA001",
            "parent_id": UUID_MAP["dept_1"],
            "tree_path": f"0,{UUID_MAP['dept_1']}",
            "sort": 1,
            "status": 1,
            "create_by": UUID_MAP["user_2"],
            "create_time": datetime.now(),
            "update_by": UUID_MAP["user_2"],
            "update_time": datetime.now(),
            "is_deleted": 0
        },
    ]

    added_count = 0
    for dept in dept_data:
        exists_query = await session.execute(
            text("SELECT 1 FROM sys_dept WHERE id = :id"),
            {"id": dept["id"]}
        )
        if not exists_query.scalar_one_or_none():
            await session.execute(
                text("""
                INSERT INTO sys_dept (id, name, code, parent_id, tree_path, sort, status, 
                                    create_by, create_time, update_by, update_time, is_deleted)
                VALUES (:id, :name, :code, :parent_id, :tree_path, :sort, :status,
                        :create_by, :create_time, :update_by, :update_time, :is_deleted)
                """),
                dept
            )
            added_count += 1

    print(f"✅ 部门数据初始化完成，新增 {added_count} 条记录")
    return added_count


# 初始化字典类型数据
async def init_sys_dict(session: AsyncSession) -> int:
    print("📚 初始化字典类型数据...")

    dict_data = [
        {"id": uuid4(), "dict_code": "gender", "name": "性别", "status": 1},
        {"id": uuid4(), "dict_code": "notice_type", "name": "通知类型", "status": 1},
        {"id": uuid4(), "dict_code": "notice_level", "name": "通知级别", "status": 1},
    ]

    added_count = 0
    for dict_item in dict_data:
        exists_query = await session.execute(
            text("SELECT 1 FROM sys_dict WHERE dict_code = :dict_code"),
            {"dict_code": dict_item["dict_code"]}
        )
        if not exists_query.scalar_one_or_none():
            dict_item.update({
                "remark": None,
                "create_time": datetime.now(),
                "create_by": UUID_MAP["user_1"],
                "update_time": datetime.now(),
                "update_by": UUID_MAP["user_1"],
                "is_deleted": 0
            })

            await session.execute(
                text("""
                INSERT INTO sys_dict (id, dict_code, name, status, remark, 
                                    create_time, create_by, update_time, update_by, is_deleted)
                VALUES (:id, :dict_code, :name, :status, :remark,
                        :create_time, :create_by, :update_time, :update_by, :is_deleted)
                """),
                dict_item
            )
            added_count += 1

    print(f"✅ 字典类型数据初始化完成，新增 {added_count} 条记录")
    return added_count


# 初始化字典项数据
async def init_sys_dict_item(session: AsyncSession) -> int:
    print("📝 初始化字典项数据...")

    # 性别字典项
    gender_items = [
        {"dict_code": "gender", "value": "1", "label": "男", "tag_type": "primary", "status": 1, "sort": 1},
        {"dict_code": "gender", "value": "2", "label": "女", "tag_type": "danger", "status": 1, "sort": 2},
        {"dict_code": "gender", "value": "0", "label": "保密", "tag_type": "info", "status": 1, "sort": 3},
    ]

    # 通知类型字典项
    notice_type_items = [
        {"dict_code": "notice_type", "value": "1", "label": "系统升级", "tag_type": "success", "status": 1, "sort": 1},
        {"dict_code": "notice_type", "value": "2", "label": "系统维护", "tag_type": "primary", "status": 1, "sort": 2},
        {"dict_code": "notice_type", "value": "3", "label": "安全警告", "tag_type": "danger", "status": 1, "sort": 3},
        {"dict_code": "notice_type", "value": "4", "label": "假期通知", "tag_type": "success", "status": 1, "sort": 4},
        {"dict_code": "notice_type", "value": "5", "label": "公司新闻", "tag_type": "primary", "status": 1, "sort": 5},
        {"dict_code": "notice_type", "value": "99", "label": "其他", "tag_type": "info", "status": 1, "sort": 99},
    ]

    # 通知级别字典项
    notice_level_items = [
        {"dict_code": "notice_level", "value": "L", "label": "低", "tag_type": "info", "status": 1, "sort": 1},
        {"dict_code": "notice_level", "value": "M", "label": "中", "tag_type": "warning", "status": 1, "sort": 2},
        {"dict_code": "notice_level", "value": "H", "label": "高", "tag_type": "danger", "status": 1, "sort": 3},
    ]

    all_items = gender_items + notice_type_items + notice_level_items

    added_count = 0
    for item in all_items:
        exists_query = await session.execute(
            text("""
            SELECT 1 FROM sys_dict_item 
            WHERE dict_code = :dict_code AND value = :value
            """),
            {"dict_code": item["dict_code"], "value": item["value"]}
        )
        if not exists_query.scalar_one_or_none():
            dict_item = {
                "id": uuid4(),
                "dict_code": item["dict_code"],
                "value": item["value"],
                "label": item["label"],
                "tag_type": item["tag_type"],
                "status": item["status"],
                "sort": item["sort"],
                "remark": None,
                "create_time": datetime.now(),
                "create_by": UUID_MAP["user_1"],
                "update_time": datetime.now(),
                "update_by": UUID_MAP["user_1"],
            }

            await session.execute(
                text("""
                INSERT INTO sys_dict_item (id, dict_code, value, label, tag_type, status, sort, remark,
                                         create_time, create_by, update_time, update_by)
                VALUES (:id, :dict_code, :value, :label, :tag_type, :status, :sort, :remark,
                        :create_time, :create_by, :update_time, :update_by)
                """),
                dict_item
            )
            added_count += 1

    print(f"✅ 字典项数据初始化完成，新增 {added_count} 条记录")
    return added_count


# 初始化角色数据
async def init_sys_role(session: AsyncSession) -> int:
    print("👥 初始化角色数据...")

    role_data = [
        {
            "id": UUID_MAP["role_1"],
            "name": "超级管理员",
            "code": "ROOT",
            "sort": 1,
            "status": 1,
            "data_scope": 1,
            "create_time": datetime.now(),
            "update_time": datetime.now(),
            "is_deleted": 0
        },
        {
            "id": UUID_MAP["role_2"],
            "name": "系统管理员",
            "code": "ADMIN",
            "sort": 2,
            "status": 1,
            "data_scope": 1,
            "create_time": datetime.now(),
            "update_time": datetime.now(),
            "is_deleted": 0
        },
        {
            "id": UUID_MAP["role_3"],
            "name": "访问游客",
            "code": "GUEST",
            "sort": 3,
            "status": 1,
            "data_scope": 3,
            "create_time": datetime.now(),
            "update_time": datetime.now(),
            "is_deleted": 0
        },
    ]

    added_count = 0
    for role in role_data:
        exists_query = await session.execute(
            text("SELECT 1 FROM sys_role WHERE id = :id"),
            {"id": role["id"]}
        )
        if not exists_query.scalar_one_or_none():
            await session.execute(
                text("""
                INSERT INTO sys_role (id, name, code, sort, status, data_scope,
                                    create_time, update_time, is_deleted)
                VALUES (:id, :name, :code, :sort, :status, :data_scope,
                        :create_time, :update_time, :is_deleted)
                """),
                role
            )
            added_count += 1

    print(f"✅ 角色数据初始化完成，新增 {added_count} 条记录")
    return added_count


# 初始化用户数据
async def init_sys_user(session: AsyncSession) -> int:
    print("👤 初始化用户数据...")

    user_data = [
        {
            "id": UUID_MAP["user_1"],
            "username": "root",
            "nickname": "有来技术",
            "gender": 0,
            "password": HASHED_PASSWORD,
            "dept_id": None,
            "avatar": "https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif",
            "mobile": "18812345677",
            "status": 1,
            "email": "youlaitech@163.com",
            "create_time": datetime.now(),
            "update_time": datetime.now(),
            "is_deleted": 0,
            "openid": None
        },
        {
            "id": UUID_MAP["user_2"],
            "username": "admin",
            "nickname": "系统管理员",
            "gender": 1,
            "password": HASHED_PASSWORD,
            "dept_id": UUID_MAP["dept_1"],
            "avatar": "https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif",
            "mobile": "18812345678",
            "status": 1,
            "email": "youlaitech@163.com",
            "create_time": datetime.now(),
            "update_time": datetime.now(),
            "is_deleted": 0,
            "openid": None
        },
        {
            "id": UUID_MAP["user_3"],
            "username": "test",
            "nickname": "测试小用户",
            "gender": 1,
            "password": HASHED_PASSWORD,
            "dept_id": UUID_MAP["dept_3"],
            "avatar": "https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif",
            "mobile": "18812345679",
            "status": 1,
            "email": "youlaitech@163.com",
            "create_time": datetime.now(),
            "update_time": datetime.now(),
            "is_deleted": 0,
            "openid": None
        },
    ]

    added_count = 0
    for user in user_data:
        exists_query = await session.execute(
            text("SELECT 1 FROM sys_user WHERE id = :id"),
            {"id": user["id"]}
        )
        if not exists_query.scalar_one_or_none():
            await session.execute(
                text("""
                INSERT INTO sys_user (id, username, nickname, gender, password, dept_id, avatar, mobile,
                                    status, email, create_time, update_time, is_deleted, openid)
                VALUES (:id, :username, :nickname, :gender, :password, :dept_id, :avatar, :mobile,
                        :status, :email, :create_time, :update_time, :is_deleted, :openid)
                """),
                user
            )
            added_count += 1

    print(f"✅ 用户数据初始化完成，新增 {added_count} 条记录")
    return added_count


# 初始化用户角色关系
async def init_sys_user_role(session: AsyncSession) -> int:
    print("🔗 初始化用户角色关系...")

    user_role_data = [
        {"user_id": UUID_MAP["user_1"], "role_id": UUID_MAP["role_1"]},
        {"user_id": UUID_MAP["user_2"], "role_id": UUID_MAP["role_2"]},
        {"user_id": UUID_MAP["user_3"], "role_id": UUID_MAP["role_3"]},
    ]

    added_count = 0
    for ur in user_role_data:
        exists_query = await session.execute(
            text("""
            SELECT 1 FROM sys_user_role 
            WHERE user_id = :user_id AND role_id = :role_id
            """),
            ur
        )
        if not exists_query.scalar_one_or_none():
            await session.execute(
                text("""
                INSERT INTO sys_user_role (user_id, role_id) 
                VALUES (:user_id, :role_id)
                """),
                ur
            )
            added_count += 1

    print(f"✅ 用户角色关系初始化完成，新增 {added_count} 条记录")
    return added_count


# 初始化菜单数据（从JSON文件加载）
async def init_sys_menu(session: AsyncSession) -> Dict[str, UUID]:
    """初始化菜单数据（从JSON文件加载）"""
    print("📊 初始化菜单数据（从JSON文件加载）...")

    menu_json_path = Path(__file__).parent / "menu_data.json"
    if not menu_json_path.exists():
        print(f"⚠️  未找到菜单数据文件：{menu_json_path}")
        return {}

    with open(menu_json_path, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)

    added_count = 0
    menu_id_map = {}

    for menu_item in menu_data:
        menu_id = UUID(menu_item["id"])
        menu_name = menu_item["name"]

        # parent_id处理
        parent_id = None
        if menu_item["parent_id"]:
            parent_id = UUID(menu_item["parent_id"])

        # 检查是否已存在
        exists_query = await session.execute(
            text("SELECT 1 FROM sys_menu WHERE id = :id"),
            {"id": menu_id}
        )

        if not exists_query.scalar_one_or_none():
            current_time = datetime.now()

            # 准备插入数据
            insert_data = {
                "id": menu_id,
                "parent_id": parent_id,
                "tree_path": menu_item["tree_path"],
                "name": menu_item["name"],
                "type": menu_item["type"],
                "route_path": menu_item["route_path"],
                "component": menu_item["component"],
                "visible": menu_item["visible"],
                "sort": menu_item["sort"],
                "icon": menu_item["icon"],
                "redirect": menu_item["redirect"],
                "create_time": current_time,
                "update_time": current_time
            }

            # 可选字段
            optional_fields = ["route_name", "perm", "always_show", "keep_alive", "params"]
            for field in optional_fields:
                if field in menu_item:
                    insert_data[field] = menu_item[field]

            columns = list(insert_data.keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            column_names = ", ".join(columns)

            await session.execute(
                text(f"""
                INSERT INTO sys_menu ({column_names})
                VALUES ({placeholders})
                """),
                insert_data
            )

            menu_id_map[menu_name] = menu_id
            added_count += 1
            print(f"  ✅ 添加菜单: {menu_name} (ID: {menu_id})")

    print(f"✅ 菜单数据初始化完成，新增 {added_count} 条记录")
    return menu_id_map


# 初始化角色菜单关系
async def init_sys_role_menu(session: AsyncSession, menu_id_map: Dict[str, UUID]) -> int:
    print("🔗 初始化角色菜单关系...")

    # 为系统管理员角色分配所有菜单权限
    admin_role_id = UUID_MAP["role_2"]
    added_count = 0

    for menu_name, menu_id in menu_id_map.items():
        exists_query = await session.execute(
            text("""
            SELECT 1 FROM sys_role_menu 
            WHERE role_id = :role_id AND menu_id = :menu_id
            """),
            {"role_id": admin_role_id, "menu_id": menu_id}
        )
        if not exists_query.scalar_one_or_none():
            await session.execute(
                text("""
                INSERT INTO sys_role_menu (role_id, menu_id) 
                VALUES (:role_id, :menu_id)
                """),
                {"role_id": admin_role_id, "menu_id": menu_id}
            )
            added_count += 1
            print(f"  ✅ 为系统管理员分配菜单权限: {menu_name}")

    print(f"✅ 角色菜单关系初始化完成，新增 {added_count} 条记录")
    return added_count


# 脚本入口
async def main():
    print("=" * 60)
    print("🚀 开始初始化youlai-admin基础数据（PostgreSQL + UUID版）")
    print("=" * 60)

    try:
        async_session_factory = create_async_db_session()

        async with async_session_factory() as session:
            async with session.begin():
                # 执行初始化（注意顺序）
                dept_count = await init_sys_dept(session)
                dict_count = await init_sys_dict(session)
                dict_item_count = await init_sys_dict_item(session)
                role_count = await init_sys_role(session)
                user_count = await init_sys_user(session)
                user_role_count = await init_sys_user_role(session)
                menu_id_map = await init_sys_menu(session)
                role_menu_count = await init_sys_role_menu(session, menu_id_map)

        # 输出最终结果
        print("=" * 60)
        print("🎉 基础数据初始化完成！")
        print("📊 统计结果：")
        print(f"  📁 部门: {dept_count} 条")
        print(f"  📚 字典类型: {dict_count} 条")
        print(f"  📝 字典项: {dict_item_count} 条")
        print(f"  👥 角色: {role_count} 条")
        print(f"  👤 用户: {user_count} 条")
        print(f"  🔗 用户角色关系: {user_role_count} 条")
        print(f"  📊 菜单: {len(menu_id_map)} 条")
        print(f"  🔗 角色菜单关系: {role_menu_count} 条")
        print("=" * 60)
        print("👤 测试账号（密码均为：123456）：")
        print(f"  root - 超级管理员")
        print(f"  admin - 系统管理员")
        print(f"  test - 测试用户")
        print("=" * 60)

    except Exception as e:
        print("=" * 60)
        print(f"❌ 初始化失败！错误原因：{str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())