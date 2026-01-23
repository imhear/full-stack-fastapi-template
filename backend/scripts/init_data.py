#!/usr/bin/env python3
"""
数据库初始化数据脚本
将MySQL数据转换为PostgreSQL格式，处理UUID主键
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models import (
    SysDept, SysDict, SysDictItem, SysMenu,
    SysRole, SysUser, sys_role_menu, sys_user_role
)

# 预先定义一些固定的UUID，确保关系正确
# 这些UUID将用于替换原MySQL中的数字ID
UUID_MAP = {
    # 部门ID映射
    "dept_1": uuid.UUID("11111111-1111-1111-1111-111111111111"),  # 有来技术
    "dept_2": uuid.UUID("22222222-2222-2222-2222-222222222222"),  # 研发部门
    "dept_3": uuid.UUID("33333333-3333-3333-3333-333333333333"),  # 测试部门

    # 角色ID映射
    "role_1": uuid.UUID("44444444-4444-4444-4444-444444444444"),  # 超级管理员
    "role_2": uuid.UUID("55555555-5555-5555-5555-555555555555"),  # 系统管理员
    "role_3": uuid.UUID("66666666-6666-6666-6666-666666666666"),  # 访问游客

    # 用户ID映射
    "user_1": uuid.UUID("77777777-7777-7777-7777-777777777777"),  # root
    "user_2": uuid.UUID("88888888-8888-8888-8888-888888888888"),  # admin
    "user_3": uuid.UUID("99999999-9999-9999-9999-999999999999"),  # test
}


def init_departments(db: Session):
    """初始化部门数据"""
    print("初始化部门数据...")

    departments = [
        SysDept(
            id=UUID_MAP["dept_1"],
            name="有来技术",
            code="YOULAI",
            parent_id=None,  # 顶级部门
            tree_path="0",
            sort=1,
            status=1,
            create_by=UUID_MAP["user_1"],
            create_time=datetime.now(),
            update_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            is_deleted=0
        ),
        SysDept(
            id=UUID_MAP["dept_2"],
            name="研发部门",
            code="RD001",
            parent_id=UUID_MAP["dept_1"],
            tree_path=f"0,{UUID_MAP['dept_1']}",
            sort=1,
            status=1,
            create_by=UUID_MAP["user_2"],
            create_time=datetime.now(),
            update_by=UUID_MAP["user_2"],
            update_time=datetime.now(),
            is_deleted=0
        ),
        SysDept(
            id=UUID_MAP["dept_3"],
            name="测试部门",
            code="QA001",
            parent_id=UUID_MAP["dept_1"],
            tree_path=f"0,{UUID_MAP['dept_1']}",
            sort=1,
            status=1,
            create_by=UUID_MAP["user_2"],
            create_time=datetime.now(),
            update_by=UUID_MAP["user_2"],
            update_time=datetime.now(),
            is_deleted=0
        ),
    ]

    for dept in departments:
        db.merge(dept)  # 使用merge避免重复插入
    db.commit()
    print(f"✅ 已插入 {len(departments)} 个部门")


def init_dicts(db: Session):
    """初始化字典数据"""
    print("初始化字典类型数据...")

    dicts = [
        SysDict(
            id=uuid.uuid4(),
            dict_code="gender",
            name="性别",
            status=1,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"],
            is_deleted=0
        ),
        SysDict(
            id=uuid.uuid4(),
            dict_code="notice_type",
            name="通知类型",
            status=1,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"],
            is_deleted=0
        ),
        SysDict(
            id=uuid.uuid4(),
            dict_code="notice_level",
            name="通知级别",
            status=1,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"],
            is_deleted=0
        ),
    ]

    for dict_type in dicts:
        db.merge(dict_type)
    db.commit()

    # 获取字典类型的ID，用于字典项关联
    gender_dict = db.query(SysDict).filter_by(dict_code="gender").first()
    notice_type_dict = db.query(SysDict).filter_by(dict_code="notice_type").first()
    notice_level_dict = db.query(SysDict).filter_by(dict_code="notice_level").first()

    print("初始化字典项数据...")
    dict_items = [
        # 性别字典项
        SysDictItem(
            id=uuid.uuid4(),
            dict_code="gender",
            value="1",
            label="男",
            tag_type="primary",
            status=1,
            sort=1,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"]
        ),
        SysDictItem(
            id=uuid.uuid4(),
            dict_code="gender",
            value="2",
            label="女",
            tag_type="danger",
            status=1,
            sort=2,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"]
        ),
        SysDictItem(
            id=uuid.uuid4(),
            dict_code="gender",
            value="0",
            label="保密",
            tag_type="info",
            status=1,
            sort=3,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"]
        ),
        # 通知类型字典项
        SysDictItem(
            id=uuid.uuid4(),
            dict_code="notice_type",
            value="1",
            label="系统升级",
            tag_type="success",
            status=1,
            sort=1,
            create_time=datetime.now(),
            create_by=UUID_MAP["user_1"],
            update_time=datetime.now(),
            update_by=UUID_MAP["user_1"]
        ),
        # ... 其他字典项按照相同格式添加
    ]

    for item in dict_items:
        db.merge(item)
    db.commit()
    print(f"✅ 已插入字典数据")


def init_users(db: Session):
    """初始化用户数据"""
    print("初始化用户数据...")

    # 注意：密码需要是哈希后的值
    # 原MySQL密码是：$2a$10$xVWsNOhHrCxh5UbpCE7/HuJ.PAOKcYAqRxD2CO2nVnJS.IAXkr5aq
    # 对应明文可能是：123456（根据原项目）
    hashed_password = "$2a$10$xVWsNOhHrCxh5UbpCE7/HuJ.PAOKcYAqRxD2CO2nVnJS.IAXkr5aq"

    users = [
        SysUser(
            id=UUID_MAP["user_1"],
            username="root",
            nickname="有来技术",
            gender=0,
            password=hashed_password,
            dept_id=None,
            avatar="https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif",
            mobile="18812345677",
            status=1,
            email="youlaitech@163.com",
            create_time=datetime.now(),
            create_by=None,
            update_time=datetime.now(),
            update_by=None,
            is_deleted=0,
            openid=None
        ),
        SysUser(
            id=UUID_MAP["user_2"],
            username="admin",
            nickname="系统管理员",
            gender=1,
            password=hashed_password,
            dept_id=2,  # 部门ID，注意这里保持原MySQL中的部门ID（因为dept_id是整数）
            avatar="https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif",
            mobile="18812345678",
            status=1,
            email="youlaitech@163.com",
            create_time=datetime.now(),
            create_by=None,
            update_time=datetime.now(),
            update_by=None,
            is_deleted=0,
            openid=None
        ),
        SysUser(
            id=UUID_MAP["user_3"],
            username="test",
            nickname="测试小用户",
            gender=1,
            password=hashed_password,
            dept_id=3,  # 部门ID
            avatar="https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif",
            mobile="18812345679",
            status=1,
            email="youlaitech@163.com",
            create_time=datetime.now(),
            create_by=None,
            update_time=datetime.now(),
            update_by=None,
            is_deleted=0,
            openid=None
        ),
    ]

    for user in users:
        db.merge(user)
    db.commit()
    print(f"✅ 已插入 {len(users)} 个用户")


def init_roles(db: Session):
    """初始化角色数据"""
    print("初始化角色数据...")

    roles = [
        SysRole(
            id=UUID_MAP["role_1"],
            name="超级管理员",
            code="ROOT",
            sort=1,
            status=1,
            data_scope=1,
            create_by=None,
            create_time=datetime.now(),
            update_by=None,
            update_time=datetime.now(),
            is_deleted=0
        ),
        SysRole(
            id=UUID_MAP["role_2"],
            name="系统管理员",
            code="ADMIN",
            sort=2,
            status=1,
            data_scope=1,
            create_by=None,
            create_time=datetime.now(),
            update_by=None,
            update_time=datetime.now(),
            is_deleted=0
        ),
        SysRole(
            id=UUID_MAP["role_3"],
            name="访问游客",
            code="GUEST",
            sort=3,
            status=1,
            data_scope=3,
            create_by=None,
            create_time=datetime.now(),
            update_by=None,
            update_time=datetime.now(),
            is_deleted=0
        ),
    ]

    for role in roles:
        db.merge(role)
    db.commit()
    print(f"✅ 已插入 {len(roles)} 个角色")


def init_menus(db: Session):
    """初始化菜单数据（简化版，只插入部分关键菜单）"""
    print("初始化菜单数据...")

    # 创建根菜单（parent_id使用全零UUID）
    root_menu_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    menus = [
        # 系统管理目录
        SysMenu(
            id=uuid.uuid4(),
            parent_id=root_menu_id,
            tree_path="0",
            name="系统管理",
            type="C",
            route_name="",
            route_path="/system",
            component="Layout",
            perm=None,
            always_show=None,
            keep_alive=0,
            visible=1,
            sort=1,
            icon="system",
            redirect="/system/user",
            create_time=datetime.now(),
            update_time=datetime.now(),
            params=None
        ),
        # 用户管理菜单
        SysMenu(
            id=uuid.uuid4(),
            parent_id=None,  # 临时设为None，下面会更新
            tree_path="",
            name="用户管理",
            type="M",
            route_name="User",
            route_path="user",
            component="system/user/index",
            perm=None,
            always_show=None,
            keep_alive=1,
            visible=1,
            sort=1,
            icon="el-icon-User",
            redirect=None,
            create_time=datetime.now(),
            update_time=datetime.now(),
            params=None
        ),
        # 角色管理菜单
        SysMenu(
            id=uuid.uuid4(),
            parent_id=None,  # 临时设为None，下面会更新
            tree_path="",
            name="角色管理",
            type="M",
            route_name="Role",
            route_path="role",
            component="system/role/index",
            perm=None,
            always_show=None,
            keep_alive=1,
            visible=1,
            sort=2,
            icon="role",
            redirect=None,
            create_time=datetime.now(),
            update_time=datetime.now(),
            params=None
        ),
    ]

    # 先插入系统管理目录
    system_menu = menus[0]
    db.merge(system_menu)
    db.flush()  # 获取生成的ID

    # 更新其他菜单的parent_id
    for menu in menus[1:]:
        menu.parent_id = system_menu.id
        menu.tree_path = f"0,{system_menu.id}"
        db.merge(menu)

    db.commit()
    print(f"✅ 已插入 {len(menus)} 个菜单")


def init_user_roles(db: Session):
    """初始化用户角色关系"""
    print("初始化用户角色关系...")

    # 使用原生SQL插入关联表数据
    user_roles = [
        (UUID_MAP["user_1"], UUID_MAP["role_1"]),  # root -> 超级管理员
        (UUID_MAP["user_2"], UUID_MAP["role_2"]),  # admin -> 系统管理员
        (UUID_MAP["user_3"], UUID_MAP["role_3"]),  # test -> 访问游客
    ]

    for user_id, role_id in user_roles:
        db.execute(
            text("""
            INSERT INTO sys_user_role (user_id, role_id) 
            VALUES (:user_id, :role_id)
            ON CONFLICT (user_id, role_id) DO NOTHING
            """),
            {"user_id": user_id, "role_id": role_id}
        )

    db.commit()
    print(f"✅ 已插入 {len(user_roles)} 个用户角色关系")


def init_role_menus(db: Session):
    """初始化角色菜单关系（简化版）"""
    print("初始化角色菜单关系...")

    # 获取所有菜单ID
    menu_ids = db.execute(
        text("SELECT id FROM sys_menu")
    ).fetchall()

    if not menu_ids:
        print("⚠️  没有找到菜单，跳过角色菜单关系初始化")
        return

    # 为系统管理员角色分配所有菜单权限
    for menu in menu_ids:
        db.execute(
            text("""
            INSERT INTO sys_role_menu (role_id, menu_id) 
            VALUES (:role_id, :menu_id)
            ON CONFLICT (role_id, menu_id) DO NOTHING
            """),
            {"role_id": UUID_MAP["role_2"], "menu_id": menu[0]}
        )

    db.commit()
    print(f"✅ 已为系统管理员角色分配 {len(menu_ids)} 个菜单权限")


def main():
    """主函数：执行所有初始化"""
    db = SessionLocal()

    try:
        print("=" * 50)
        print("开始初始化数据库数据...")
        print("=" * 50)

        # 注意执行顺序：先创建基础数据，再创建依赖数据
        init_departments(db)
        init_dicts(db)
        init_roles(db)
        init_menus(db)
        init_users(db)
        init_user_roles(db)
        init_role_menus(db)

        print("=" * 50)
        print("✅ 数据库数据初始化完成！")
        print("=" * 50)

        # 验证数据
        print("\n📊 数据统计：")
        tables = {
            "sys_dept": "部门",
            "sys_dict": "字典类型",
            "sys_dict_item": "字典项",
            "sys_menu": "菜单",
            "sys_role": "角色",
            "sys_user": "用户"
        }

        for table, name in tables.items():
            count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {name}: {count} 条记录")

        print("\n👤 测试账号：")
        print("  root / 123456 (超级管理员)")
        print("  admin / 123456 (系统管理员)")
        print("  test / 123456 (测试用户)")

    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()