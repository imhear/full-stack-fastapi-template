"""
DI容器
项目核心框架文件
backend/app/di/container.py
"""
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine as create_sync_engine
from contextlib import contextmanager, asynccontextmanager
import redis.asyncio as redis  # 修改：使用异步Redis

# 导入新增的Repo和Service
from app.repositories.sys_user_repository import UserRepository
from app.repositories.sys_permission_repository import PermissionRepository
from app.repositories.sys_role_repository import RoleRepository
from app.services.captcha_service import CaptchaService # 新增：导入CaptchaService

from app.services.sys_user_service import UserService
from app.services.sys_permission_service import PermissionService
from app.services.sys_auth_service import AuthService
from app.services.sys_role_service import RoleService
from app.services.redis_service import RedisService  # 新增：导入RedisService

from app.core.config import settings


# 会话工厂（请求级会话，用完关闭）- 现有逻辑无修改
@asynccontextmanager
async def async_db_factory(async_session_factory: sessionmaker):
    session: AsyncSession = async_session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

@contextmanager
def sync_db_factory(engine):
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

# 新增：Redis连接工厂
@asynccontextmanager
async def redis_client_factory():
    """Redis客户端工厂（异步）"""
    redis_client = None
    try:
        if settings.REDIS_USE_POOL:
            redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding=settings.REDIS_ENCODING,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_keepalive=True,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            )
        else:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                encoding=settings.REDIS_ENCODING,
                socket_keepalive=True,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            )
        # 测试连接
        await redis_client.ping()
        yield redis_client
    finally:
        if redis_client:
            await redis_client.close()


class Container(containers.DeclarativeContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, deepcopy=False, auto_wire=True, **kwargs)

    # 1. 底层：数据库引擎（单例，全局唯一）- 现有逻辑无修改
    sync_engine = providers.Singleton(
        create_sync_engine,
        str(settings.SQLALCHEMY_DATABASE_URI).replace("+psycopg", "+psycopg2"),
        echo=False,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

    async_engine = providers.Singleton(
        create_async_engine,
        str(settings.SQLALCHEMY_DATABASE_URI),
        echo=False,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

    # 2. 新增：异步Redis客户端（Resource，请求级）
    redis_client = providers.Resource(
        redis_client_factory
    )

    # 3. 新增：Redis服务（工厂，可复用）
    redis_service = providers.Factory(
        RedisService,
        redis_client=redis_client
    )

    # 新增：CaptchaService服务
    captcha_service = providers.Factory(
        CaptchaService,
        redis_service=redis_service
    )

    # 2. 中层：会话工厂（单例，全局唯一）- 现有逻辑无修改
    async_session_factory = providers.Singleton(
        sessionmaker,
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )

    # 3. 请求级会话（给Service用）- 现有逻辑无修改
    async_db = providers.Resource(
        async_db_factory,
        async_session_factory=async_session_factory
    )

    sync_db = providers.Resource(
        sync_db_factory,
        engine=sync_engine
    )

    # 4. Repo层：注入会话工厂（新增2个Repo，对齐现有风格）
    user_repository = providers.Factory(
        UserRepository,
        async_session_factory=async_session_factory
    )
    permission_repository = providers.Factory(
        PermissionRepository,
        async_session_factory=async_session_factory
    )
    role_repository = providers.Factory(
        RoleRepository,
        async_session_factory=async_session_factory
    )

    # 5. Service层：注入Repo和请求级会话（新增2个Service，对齐现有风格）
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        async_db_session=async_db,
        redis_service=redis_service  # 新增：注入RedisService
    )
    permission_service = providers.Factory(
        PermissionService,
        permission_repository=permission_repository,
        async_db_session=async_db,
        redis_service=redis_service  # 新增：注入RedisService
    )
    auth_service = providers.Factory(
        AuthService,
        user_repository=user_repository,
        async_db_session=async_db,
        redis_service=redis_service  # 新增：注入RedisService
    )
    role_service = providers.Factory(
        RoleService,
        role_repository=role_repository,
        permission_repository=permission_repository,
        user_repository=user_repository,
        async_db_session=async_db,
        redis_service=redis_service  # 新增：注入RedisService
    )

    # 6. 模块扫描：新增API端点模块（确保DI能扫描到新增接口）
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.v1.endpoints.users",
            "app.api.v1.endpoints.login",
            "app.api.v1.endpoints.roles",
            "app.api.deps"
        ]
    )
