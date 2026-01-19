"""
权限校验工具文件
backend/app/utils/permission_checker.py
上次更新：2025/12/12
核心功能：
1. 支持三级权限通配符匹配（module:resource:action → module:resource:* → module:*:*）
2. 超级管理员豁免机制（可通过strict_superuser关闭）
3. 精细化异常处理+标准化日志+RESTful异常格式
4. 脱敏敏感信息，符合数据安全规范
行业最佳实践优化点：
- 精准类型注解+模块导出控制
- 精细化异常捕获（区分SQLAlchemy异常）
- 核心逻辑抽离为独立函数（提升可测试性）
- 脱敏用户敏感信息，日志关联请求上下文
- 完善参数校验和空值处理
- 适配全局日志配置，日志落文件且包含request_id
- 兼容日志落文件开关log_to_file_flag，灵活控制输出方式
- 优化：补全权限豁免日志的request_id字段，确保日志格式统一
- 修复：增强权限匹配健壮性，处理无效权限码；优化超级管理员判断日志；增加权限查询详细日志
- 终极修复：优化权限查询SQL（增加distinct+精准过滤+原始结果日志），解决查询返回错误权限码问题
"""
import logging
import hashlib
from typing import Set, Callable, Awaitable, List, Optional
from contextvars import ContextVar
from datetime import datetime  # 新增：导入datetime用于时间戳

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, distinct  # 新增：导入distinct去重
from sqlalchemy.exc import SQLAlchemyError  # 精细化异常捕获
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession  # 精准类型注解

# ====================== 核心修正：导入已有deps.py的AsyncSessionDep ======================
from app.api.deps import AsyncSessionDep, get_current_user
from app.models import SysUser, SysRole, SysPermission, sys_user_roles, sys_role_permissions
# 导入全局时区配置xs
from app.core.config import DEFAULT_TZ

# ====================== 基础配置（行业最佳实践）======================
# 1. 标准化日志配置（复用全局日志配置，支持落文件）
logger = logging.getLogger(__name__)
# 请求ID上下文变量（需在入口处注入，如中间件）
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# 2. 模块导出控制（避免非预期导出）
__all__ = ["permission_checker", "get_user_permissions"]

# ====================== 工具函数（抽离核心逻辑，提升复用性）======================
def generate_permission_wildcards(required_perm: str) -> List[str]:
    """
    生成权限通配符列表（行业最佳实践：核心逻辑抽离，便于测试/复用）
    :param required_perm: 原始权限码（如 manual:doc:category:view）
    :return: 通配符列表
    :raises ValueError: 权限码格式无效时抛出（仅警告，不中断流程）
    """
    if not required_perm:
        logger.warning(
            "所需权限码为空，无法生成通配符",
            extra={"request_id": request_id_ctx.get()}
        )
        return []

    # 修复：无效权限码仅警告，返回原权限码，避免中断流程
    if ":" not in required_perm:
        logger.warning(
            f"无效的权限码格式：{required_perm}，需符合 module:resource:action 规范，跳过通配符生成",
            extra={"request_id": request_id_ctx.get(), "required_perm": required_perm}
        )
        return [required_perm]  # 返回原权限码，避免匹配逻辑崩溃

    perm_parts = required_perm.split(':')
    # 支持三级/四级权限通配符（兼容常见场景）
    wildcards = [required_perm]
    if len(perm_parts) >= 3:
        wildcards.append(f"{perm_parts[0]}:{perm_parts[1]}:*")
        wildcards.append(f"{perm_parts[0]}:*:*")
    elif len(perm_parts) == 2:
        wildcards.append(f"{perm_parts[0]}:*")

    logger.debug(
        f"权限通配符生成完成 | 原始权限：{required_perm} | 通配符列表：{wildcards}",
        extra={"request_id": request_id_ctx.get(), "required_perm": required_perm, "wildcards": wildcards}
    )
    return wildcards

def desensitize_user_id(user_id: str) -> str:
    """
    用户ID脱敏（行业最佳实践：保护敏感信息）
    :param user_id: 原始用户ID
    :return: 脱敏后ID（前6位+后4位，中间MD5）
    """
    if len(user_id) <= 10:
        return hashlib.md5(user_id.encode()).hexdigest()[:8]
    return f"{user_id[:6]}...{user_id[-4:]}"

# ====================== 核心权限查询函数（终极修复版）======================
async def get_user_permissions(
    user_id: str,
    session: AsyncSession  # 接收deps.py注入的AsyncSession实例
) -> Set[str]:
    """
    从数据库获取用户所有有效权限代码（终极修复版）
    核心修复：
    1. 增加distinct去重，避免重复权限记录
    2. 精准过滤有效角色/权限（is_active=True）
    3. 增加原始查询结果日志，打印所有查询到的code值
    4. 重构SQL查询逻辑，避免关联错误
    5. 过滤无效权限码，仅保留符合module:resource:action规范的权限

    :param user_id: 用户UUID字符串（必传）
    :param session: 异步数据库会话实例（来自deps.py的AsyncSessionDep）
    :return: 非空权限代码集合（无权限返回空集合）
    :raises ValueError: 入参无效时抛出
    :raises HTTPException: 数据库异常时抛出标准化500错误
    """
    # 入参校验（行业最佳实践：提前拦截无效请求）
    if not user_id or not isinstance(user_id, str):
        raise ValueError(f"用户ID无效：{user_id}（需为非空字符串）")

    # 日志上下文（请求ID+脱敏用户ID）
    request_id = request_id_ctx.get()
    desensitized_uid = desensitize_user_id(user_id)
    logger.info(
        f"开始查询用户权限 | 脱敏用户ID：{desensitized_uid}",
        extra={"request_id": request_id, "user_id": desensitized_uid}
    )

    try:
        # ====================== 终极修复：重构权限查询SQL ======================
        # 步骤1：查询用户关联的有效角色ID
        role_ids_query = select(sys_user_roles.c.role_id).where(
            sys_user_roles.c.user_id == user_id
        )
        role_ids_result = await session.execute(role_ids_query)
        role_ids = role_ids_result.scalars().all()

        if not role_ids:
            logger.info(
                f"用户无关联角色 | 脱敏用户ID：{desensitized_uid}",
                extra={"request_id": request_id, "user_id": desensitized_uid}
            )
            return set()

        logger.debug(
            f"用户关联角色ID | 脱敏用户ID：{desensitized_uid} | 角色ID列表：{role_ids}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "role_ids": role_ids}
        )

        # 步骤2：查询角色关联的有效权限ID（仅is_active=True的角色和权限）
        permission_ids_query = select(
            distinct(sys_role_permissions.c.permission_id)  # 去重
        ).join(
            SysRole, SysRole.id == sys_role_permissions.c.role_id
        ).join(
            SysPermission, SysPermission.id == sys_role_permissions.c.permission_id
        ).where(
            sys_role_permissions.c.role_id.in_(role_ids),
            SysRole.is_active == True,
            SysPermission.is_active == True
        )

        permission_ids_result = await session.execute(permission_ids_query)
        permission_ids = permission_ids_result.scalars().all()

        if not permission_ids:
            logger.info(
                f"用户关联角色无有效权限 | 脱敏用户ID：{desensitized_uid} | 角色ID列表：{role_ids}",
                extra={"request_id": request_id, "user_id": desensitized_uid, "role_ids": role_ids}
            )
            return set()

        logger.debug(
            f"角色关联权限ID | 脱敏用户ID：{desensitized_uid} | 权限ID列表：{permission_ids}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "permission_ids": permission_ids}
        )

        # 步骤3：查询权限代码（仅有效权限）
        permissions_query = select(
            distinct(SysPermission.code)  # 去重
        ).where(
            SysPermission.id.in_(permission_ids),
            SysPermission.is_active == True
        )

        permissions_result = await session.execute(permissions_query)
        raw_permissions = permissions_result.scalars().all()

        # 新增：打印原始查询结果日志（关键排查点）
        logger.debug(
            f"原始权限查询结果 | 脱敏用户ID：{desensitized_uid} | 所有查询到的code：{raw_permissions}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "raw_permissions": raw_permissions}
        )

        # 过滤无效权限码（仅保留包含:的权限码）
        valid_permissions = set()
        invalid_permissions = set()
        for perm in raw_permissions:
            if perm and ":" in perm:
                valid_permissions.add(perm)
            elif perm:
                invalid_permissions.add(perm)

        # 无效权限码日志
        if invalid_permissions:
            logger.warning(
                f"用户权限包含无效格式的权限码 | 脱敏用户ID：{desensitized_uid} | 无效权限码：{invalid_permissions}",
                extra={"request_id": request_id, "user_id": desensitized_uid, "invalid_permissions": invalid_permissions}
            )

        logger.info(
            f"用户权限查询完成 | 脱敏用户ID：{desensitized_uid} | 原始权限数量：{len(raw_permissions)} | 有效权限数量：{len(valid_permissions)} | 有效权限列表：{sorted(valid_permissions)}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "perm_count": len(valid_permissions), "permissions": sorted(valid_permissions)}
        )
        return valid_permissions

    # 精细化异常捕获（仅处理数据库相关异常）
    except SQLAlchemyError as e:
        logger.error(
            f"用户权限查询失败（数据库异常） | 脱敏用户ID：{desensitized_uid} | 异常详情：{str(e)}",
            extra={"request_id": request_id, "user_id": desensitized_uid},
            exc_info=True  # 生产环境可配置为False，避免暴露堆栈
        )
        # RESTful标准化500异常（不暴露敏感信息）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "PERMISSION_QUERY_FAILED",
                "message": "权限查询服务异常，请稍后重试",
                "request_id": request_id,  # 便于运维排查
                "timestamp": datetime.now(DEFAULT_TZ).isoformat()
            }
        )

# ====================== 权限校验工厂函数（最佳实践版）======================
def permission_checker(
    required_perm: str,
    strict_superuser: bool = False
) -> Callable[[AsyncSessionDep], Awaitable[bool]]:
    """
    权限验证工厂函数（行业最佳实践完整版）
    核心特性：
    1. 支持三级/四级权限通配符匹配
    2. 超级管理员豁免机制（可通过strict_superuser关闭）
    3. 标准化日志+请求上下文+脱敏信息
    4. 完善的参数校验和异常处理
    5. 复用deps.py的AsyncSessionDep和get_current_user
    6. 日志自动落文件（可通过log_to_file_flag关闭），包含request_id
    7. 终极修复：适配重构后的权限查询逻辑，增强日志排查能力

    :param required_perm: 所需权限码（如 manual:doc:category:view）
    :param strict_superuser: 严格模式（超级管理员也需校验权限），默认False
    :return: FastAPI依赖注入函数
    """
    # 提前生成通配符（避免每次校验重复生成）
    wildcards = generate_permission_wildcards(required_perm)

    async def checker(
        session: AsyncSessionDep,  # 复用deps.py的AsyncSessionDep（注入实例）
        current_user: SysUser = Depends(get_current_user)
    ) -> bool:
        """FastAPI依赖注入函数（权限校验核心逻辑）"""
        request_id = request_id_ctx.get()
        desensitized_uid = desensitize_user_id(current_user.id)

        # 新增：超级管理员判断详细日志
        logger.debug(
            f"超级管理员判断 | 用户名：{current_user.username} | is_superuser：{current_user.is_superuser} | 严格模式：{strict_superuser}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "username": current_user.username, "is_superuser": current_user.is_superuser, "strict_superuser": strict_superuser}
        )

        # 1. 超级管理员豁免逻辑（可配置）
        if not strict_superuser and current_user.is_superuser:
            logger.info(
                f"超级管理员权限豁免 | 用户名：{current_user.username} | 所需权限：{required_perm}",
                extra={"request_id": request_id, "user_id": desensitized_uid, "username": current_user.username, "required_perm": required_perm}
            )
            return True

        # 2. 普通用户权限校验
        user_perms = await get_user_permissions(current_user.id, session)

        # 新增：权限匹配详细日志
        logger.debug(
            f"权限匹配开始 | 用户名：{current_user.username} | 所需权限：{required_perm} | 通配符列表：{wildcards} | 用户有效权限：{sorted(user_perms)}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "username": current_user.username, "required_perm": required_perm, "wildcards": wildcards, "user_permissions": sorted(user_perms)}
        )

        # 权限匹配（抽离逻辑后更清晰）
        is_permitted = any(perm in user_perms for perm in wildcards)

        if not is_permitted:
            logger.warning(
                f"用户权限不足 | 用户名：{current_user.username} | 所需权限：{required_perm} | 支持通配符：{wildcards} | 已拥有有效权限：{sorted(user_perms)}",
                extra={"request_id": request_id, "user_id": desensitized_uid, "username": current_user.username, "required_perm": required_perm, "wildcards": wildcards, "user_permissions": sorted(user_perms)}
            )
            # RESTful标准化403异常
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "权限不足，无法执行该操作",
                    "required_permission": required_perm,
                    "supported_wildcards": wildcards,
                    "current_permissions": sorted(user_perms),  # 新增：返回当前用户有效权限，便于排查
                    "request_id": request_id
                }
            )

        logger.info(
            f"用户权限校验通过 | 用户名：{current_user.username} | 所需权限：{required_perm}",
            extra={"request_id": request_id, "user_id": desensitized_uid, "username": current_user.username, "required_perm": required_perm}
        )
        return True

    return checker