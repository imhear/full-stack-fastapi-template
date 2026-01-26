# app/services/sys_dept_service.py
"""
部门服务层
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException

from app.models import SysDept
from app.repositories.sys_dept_repository import DeptRepository
from app.schemas.sys_dept import DeptCreate, DeptUpdate, DeptTreeNode
from app.core.exceptions import ResourceNotFound, BadRequest


class DeptService:
    """
    部门服务
    """

    def __init__(self, dept_repository: DeptRepository, async_db_session: AsyncSession):
        self.dept_repository = dept_repository
        self.async_db_session = async_db_session
        print(f"🔍 DEBUG: DeptService初始化完成")
        print(f"  dept_repository: {type(dept_repository)}")
        print(f"  async_db_session: {async_db_session}")

    async def get_dept_options(self) -> List[Dict[str, Any]]:
        """
        获取部门下拉选项（树形结构）

        返回格式：
        [
            {
                "value": "部门ID字符串",
                "label": "部门名称",
                "tag": "部门编码",
                "children": [...]
            }
        ]
        """
        # 1. 获取所有启用的部门
        all_depts = await self.dept_repository.get_all_enabled_depts()

        # 2. 构建部门映射表
        dept_map = {}
        for dept in all_depts:
            dept_map[dept.id] = {
                "id": str(dept.id),
                "name": dept.name,
                "code": dept.code,
                "parent_id": dept.parent_id,
                "children": []
            }

        # 3. 构建树形结构
        root_depts = []
        for dept_id, dept_info in dept_map.items():
            if dept_info["parent_id"] is None:
                root_depts.append(dept_info)
            else:
                parent_info = dept_map.get(dept_info["parent_id"])
                if parent_info:
                    parent_info["children"].append(dept_info)

        # 4. 转换为前端需要的格式
        def build_tree_nodes(dept_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """递归构建树节点"""
            nodes = []
            for dept in dept_list:
                node = {
                    "value": dept["id"],
                    "label": dept["name"],
                    "tag": dept["code"]
                }
                if dept["children"]:
                    node["children"] = build_tree_nodes(dept["children"])
                nodes.append(node)
            return nodes

        return build_tree_nodes(root_depts)

    async def get_dept_options_map(self) -> Dict[str, str]:
        """
        获取部门ID到名称的映射字典

        返回格式：
        {
            "11111111-1111-1111-1111-111111111111": "有来技术",
            "22222222-2222-2222-2222-222222222222": "研发部门",
            "33333333-3333-3333-3333-333333333333": "测试部门"
        }

        如果将来需要缓存或Redis支持，可以在此方法内部实现
        """
        try:
            # 获取所有启用的部门
            all_depts = await self.dept_repository.get_all_enabled_depts()

            # 构建ID到名称的映射字典
            dept_map = {}
            for dept in all_depts:
                dept_id_str = str(dept.id)
                dept_map[dept_id_str] = dept.name

            print(f"🔍 DEBUG: get_dept_options_map 返回 {len(dept_map)} 个部门映射")
            return dept_map

        except Exception as e:
            print(f"❌ 获取部门映射失败: {str(e)}")
            # 返回空字典，避免影响主流程
            return {}

    async def get_dept_and_sub_dept_ids(self, dept_id: str) -> List[str]:
        """
        获取部门及其所有子部门的ID列表（优化版）

        使用tree_path字段直接查找子部门，避免递归查询
        """
        try:
            # 1. 首先获取目标部门
            target_dept = await self.dept_repository.get_by_id(dept_id)
            if not target_dept:
                return [dept_id]  # 如果部门不存在，只返回当前ID

            # 2. 构建tree_path模式
            # tree_path格式如：0,11111111-1111-1111-1111-111111111111,22222222-2222-2222-2222-222222222222
            # 我们要查找所有tree_path包含目标部门ID的部门
            target_path_pattern = f"%{dept_id}%"

            # 3. 查询所有子部门
            sub_depts = await self.dept_repository.get_depts_by_tree_path_pattern(target_path_pattern)

            # 4. 提取ID并去重
            dept_ids = {dept_id}  # 包含目标部门
            for dept in sub_depts:
                dept_ids.add(str(dept.id))

            return list(dept_ids)

        except Exception as e:
            print(f"获取部门子部门ID列表失败: {str(e)}")
            # 降级：只返回当前部门ID
            return [dept_id]

    async def get_dept_tree(self) -> List[Dict[str, Any]]:
        """
        获取完整的部门树

        返回格式：
        [
            {
                "value": "部门ID",
                "label": "部门名称",
                "children": [...]
            }
        ]
        """
        # 获取根部门
        root_depts = await self.dept_repository.get_root_depts()

        # 递归构建树
        async def build_tree(dept: SysDept) -> Dict[str, Any]:
            """递归构建部门树"""
            children_depts = await self.dept_repository.get_children_depts(dept.id)

            node = {
                "value": str(dept.id),
                "label": dept.name
            }

            if children_depts:
                node["children"] = []
                for child in children_depts:
                    child_tree = await build_tree(child)
                    node["children"].append(child_tree)

            return node

        tree_result = []
        for root_dept in root_depts:
            tree_node = await build_tree(root_dept)
            tree_result.append(tree_node)

        return tree_result

    async def get_dept_by_id(self, dept_id: UUID) -> Optional[SysDept]:
        """根据ID获取部门"""
        dept = await self.dept_repository.get_by_id(dept_id)
        if not dept:
            raise ResourceNotFound(detail=f"部门ID '{dept_id}' 不存在")
        return dept

    async def create_dept(self, dept_in: DeptCreate) -> Dict[str, Any]:
        """创建部门"""
        # 1. 验证部门编码唯一性
        existing_dept = await self.dept_repository.get_by_code(dept_in.code)
        if existing_dept:
            raise BadRequest(detail=f"部门编码 '{dept_in.code}' 已存在")

        # 2. 验证父部门
        if dept_in.parent_id:
            parent_dept = await self.dept_repository.get_by_id(dept_in.parent_id)
            if not parent_dept:
                raise BadRequest(detail=f"父部门ID '{dept_in.parent_id}' 不存在")
            if parent_dept.status != 1:
                raise BadRequest(detail="父部门已停用，无法创建子部门")

        # 3. 创建部门
        async with self.dept_repository.transaction() as session:
            dept_data = dept_in.model_dump()
            dept = await self.dept_repository.create(dept_data, session)

            # 构建返回数据
            return {
                "id": str(dept.id),
                "name": dept.name,
                "code": dept.code,
                "parent_id": str(dept.parent_id) if dept.parent_id else None,
                "sort": dept.sort,
                "status": dept.status,
                "create_time": dept.create_time
            }

    async def update_dept(self, dept_id: UUID, dept_update: DeptUpdate) -> Dict[str, Any]:
        """更新部门"""
        # 1. 获取部门
        dept = await self.get_dept_by_id(dept_id)

        # 2. 验证部门编码唯一性（如果修改）
        if dept_update.code and dept_update.code != dept.code:
            existing_dept = await self.dept_repository.get_by_code(dept_update.code)
            if existing_dept:
                raise BadRequest(detail=f"部门编码 '{dept_update.code}' 已存在")

        # 3. 验证父部门（如果修改）
        if dept_update.parent_id and dept_update.parent_id != dept.parent_id:
            # 不能将自己设为父部门
            if dept_update.parent_id == dept_id:
                raise BadRequest(detail="不能将自己设为父部门")

            # 检查父部门是否存在
            parent_dept = await self.dept_repository.get_by_id(dept_update.parent_id)
            if not parent_dept:
                raise BadRequest(detail=f"父部门ID '{dept_update.parent_id}' 不存在")

            # 检查是否形成循环引用
            if await self._is_circular_reference(dept_id, dept_update.parent_id):
                raise BadRequest(detail="不能将子部门设为父部门，避免循环引用")

        # 4. 更新部门
        async with self.dept_repository.transaction() as session:
            update_data = dept_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(dept, key, value)

            updated_dept = await self.dept_repository.update(dept, session)

            # 构建返回数据
            return {
                "id": str(updated_dept.id),
                "name": updated_dept.name,
                "code": updated_dept.code,
                "parent_id": str(updated_dept.parent_id) if updated_dept.parent_id else None,
                "sort": updated_dept.sort,
                "status": updated_dept.status,
                "update_time": updated_dept.update_time
            }

    async def delete_dept(self, dept_id: UUID) -> Dict[str, Any]:
        """删除部门"""
        # 1. 检查部门是否存在
        dept = await self.get_dept_by_id(dept_id)

        # 2. 检查是否有子部门
        has_children = await self.dept_repository.check_has_children(dept_id)
        if has_children:
            raise BadRequest(detail="存在子部门，无法删除")

        # 3. 检查部门下是否有用户
        has_users = await self.dept_repository.check_has_users(dept_id)
        if has_users:
            raise BadRequest(detail="部门下存在用户，无法删除")

        # 4. 软删除部门
        async with self.dept_repository.transaction() as session:
            success = await self.dept_repository.delete(dept_id, session)
            if not success:
                raise ResourceNotFound(detail=f"部门ID '{dept_id}' 不存在")

            return {
                "deleted": True,
                "id": str(dept_id),
                "name": dept.name
            }

    # ==================== 辅助方法 ====================


    async def _is_circular_reference(self, dept_id: UUID, parent_id: UUID) -> bool:
        """检查是否形成循环引用"""
        # 递归检查父部门是否是被修改部门的子部门
        current_parent_id = parent_id
        while current_parent_id:
            if current_parent_id == dept_id:
                return True
            parent_dept = await self.dept_repository.get_by_id(current_parent_id)
            if not parent_dept or not parent_dept.parent_id:
                break
            current_parent_id = parent_dept.parent_id
        return False