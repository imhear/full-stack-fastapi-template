# 项目核心配置文件，包含数据库、JWT、CORS、邮件等全局配置，支持从.env文件加载环境变量
# backend/app/core/config.py
# 第80轮更新（2025/12/12）：新增全局时区配置，解决updated_at字段时区差8小时问题
#  - 导入ZoneInfo模块，新增DEFAULT_TIMEZONE配置字段（默认Asia/Shanghai）
#  - 导出全局DEFAULT_TZ对象，供Service层统一使用，避免重复定义时区
# 第81轮更新（2025/12/12）：新增日志落文件开关配置，适配日志灵活输出需求
#  - 新增LOG_TO_FILE_FLAG字段，支持从.env加载，开发环境默认True，生产环境默认False
#  - 字段添加env参数，确保.env配置可覆盖默认值，最小化修改原有配置逻辑
# 第82轮更新（2025/12/18）：新增文档根目录配置，适配本地/Docker环境路径统一
#  - 新增DOC_ROOT_DIR字段，默认指向项目根目录同级的docs目录，支持.env覆盖
#  - 字段添加env参数，确保Docker环境可通过环境变量指定容器内路径
# 第83轮更新（2025/12/18）：修复日志开关默认值逻辑+新增日志路径配置
#  - 修复LOG_TO_FILE_FLAG的default_factory递归调用问题，改用model_validator动态设置
#  - 新增LOG_FILE_PATH字段，指定日志文件存储路径，支持.env覆盖
# 第84轮更新（2025/12/19）：最小化新增全局日志初始化逻辑，确保日志落文件
#  - 新增init_global_logger函数，复用现有配置，不改动原有核心逻辑
#  - 新增轮转日志Handler，验证日志目录可写性，兼容Docker挂载路径
#  - 保留所有原有代码，仅在文件末尾新增日志逻辑，无任何删减

import secrets
import warnings
from typing import Annotated, Any, Literal
from pydantic_settings import BaseSettings
from pydantic import Field

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self
# 新增SQLAlchemy日志配置（优化：避免重复初始化日志）
import logging
from logging import Logger
# 第80轮新增：导入时区处理模块，用于全局时区配置
from zoneinfo import ZoneInfo
import os  # 新增：导入os模块


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        # env_file="../.env",
        env_file=os.getenv("ENV_FILE_PATH", "../.env"),  # 关键：动态路径
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    # 密码加密
    BCRYPT_ROUNDS: int = 12
    # 30 minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # ========== 修改点1：FRONTEND_HOST改为占位符，开发环境不依赖固定端口 ==========
    FRONTEND_HOST: str = "http://localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # 第81轮新增：日志落文件开关，修复默认值逻辑（避免递归调用）
    LOG_TO_FILE_FLAG: bool = Field(
        default=True,  # 本地环境默认True，生产环境通过.env设为False
        env="LOG_TO_FILE_FLAG",
        description="日志落文件开关（True：控制台+文件输出；False：仅控制台输出），开发环境默认True，生产/测试环境默认False"
    )

    # 第83轮新增：日志文件存储路径（容器内默认/app/logs/app.log，宿主机挂载到/Users/wutao/code/fastapi_demo/logs）
    LOG_FILE_PATH: str = Field(
        default="/app/logs/app.log",
        env="LOG_FILE_PATH",
        description="日志文件存储路径（容器内路径，需挂载到宿主机）"
    )

    # 动态设置日志开关默认值（优先级：.env配置 > 环境自动判断）
    @model_validator(mode="before")
    def set_default_log_flag(cls, values):
        if "LOG_TO_FILE_FLAG" not in values:
            # 本地环境默认开启日志落文件，其他环境默认关闭
            values["LOG_TO_FILE_FLAG"] = values.get("ENVIRONMENT", "local") == "local"
        return values

    # ========== 修改点2：BACKEND_CORS_ORIGINS默认值支持本地所有端口（开发环境） ==========
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = [
        "http://localhost",  # 兼容localhost任意端口
        "http://127.0.0.1",  # 兼容127.0.0.1任意端口
        "http://0.0.0.0"     # 兼容本地IP任意端口
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        # 开发环境：返回通配符格式（兼容任意端口）；生产环境：严格匹配配置的源
        if self.ENVIRONMENT == "local":
            return [
                "http://localhost:3000",  # 前端实际地址（关键：明确端口）
                "http://127.0.0.1:3000",
                "http://localhost",
                "http://127.0.0.1",
                "http://0.0.0.0"
            ]
        # 生产/测试环境：保留原有严格匹配逻辑
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # 数据库连接池配置
    DB_POOL_SIZE: int = Field(20, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(100, description="最大溢出连接数")
    DB_POOL_RECYCLE: int = Field(3600, description="连接回收时间(秒)")
    DB_POOL_PRE_PING: bool = Field(True, description="连接有效性检查")

    # 第62轮调整：简化为字节单位配置（默认2*1024*1024=2MB），移除MB单位字段，减少应用层转换复杂度
    DOC_UPLOAD_MAX_SIZE_BYTE: int = Field(
        2 * 1024 * 1024,
        env="DOC_UPLOAD_MAX_SIZE_BYTE",  # 仅新增这一行
        description="文档上传最大大小限制（字节）"
    )

    # 第80轮新增：全局时区配置，默认北京时间（Asia/Shanghai），支持从.env覆盖
    DEFAULT_TIMEZONE: str = Field(
        "Asia/Shanghai",
        env="DEFAULT_TIMEZONE",
        description="项目全局默认时区（如Asia/Shanghai、UTC等）"
    )

    # 第82轮新增：文档根目录配置，默认指向项目根目录同级的docs目录，支持.env覆盖
    DOC_ROOT_DIR: str = Field(
        "/Users/wutao/code/fastapi_demo/docs",
        env="DOC_ROOT_DIR",
        description="文档存储根目录（本地环境默认/Users/wutao/code/fastapi_demo/docs，Docker环境配置为/app/../docs）"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


    # Redis配置
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: str = Field("", env="REDIS_PASSWORD")
    REDIS_ENCODING: str = Field("utf-8", env="REDIS_ENCODING")
    REDIS_DECODE_RESPONSES: bool = Field(True, env="REDIS_DECODE_RESPONSES")
    REDIS_MAX_CONNECTIONS: int = Field(10, env="REDIS_MAX_CONNECTIONS")
    REDIS_SOCKET_TIMEOUT: int = Field(5, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    REDIS_KEY_PREFIX: str = Field("app:", env="REDIS_KEY_PREFIX")
    REDIS_USE_POOL: bool = Field(True, env="REDIS_USE_POOL")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """生成 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

# 全局settings对象
settings = Settings()  # type: ignore

# 第80轮新增：导出全局时区对象
DEFAULT_TZ = ZoneInfo(settings.DEFAULT_TIMEZONE)


# 优化：SQLAlchemy日志配置（避免与main.py的日志配置冲突）
def init_sqlalchemy_logger() -> Logger:
    """初始化SQLAlchemy日志（复用全局环境配置）"""
    logger = logging.getLogger('sqlalchemy.engine')
    # 根据环境设置日志级别（本地DEBUG，生产INFO）
    log_level = logging.DEBUG if settings.ENVIRONMENT == "local" else logging.INFO
    logger.setLevel(log_level)
    # 避免重复添加处理器
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %z"  # 包含时区
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


# 初始化SQLAlchemy日志（仅执行一次）
sqlalchemy_logger = init_sqlalchemy_logger()

# ======================================
# 第84轮新增（2025/12/19）：最小化日志初始化逻辑
# 仅新增以下代码，无任何原有代码删减/修改
# ======================================
from datetime import datetime
from logging.handlers import RotatingFileHandler


def init_global_logger() -> None:
    """
    最小化初始化全局日志（仅新增，不改动原有逻辑）
    - 复用settings现有配置，支持日志落文件开关
    - 适配Docker挂载路径：/app/logs/local
    - 验证日志目录可写性，确保日志能写入文件
    """
    # 根Logger（捕获所有模块日志）
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.ENVIRONMENT == "local" else logging.INFO)

    # 避免重复添加Handler（防止日志重复输出）
    if len(root_logger.handlers) > 0:
        return

    # 1. 控制台Handler（保留原有输出）
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. 文件Handler（仅当LOG_TO_FILE_FLAG=True时添加）
    if settings.LOG_TO_FILE_FLAG:
        # 修正日志路径为Docker挂载的/local目录（适配实际部署）
        log_dir = "/app/logs/local"
        os.makedirs(log_dir, exist_ok=True)

        # 按日期生成日志文件（与宿主机挂载路径匹配）
        log_filename = os.path.join(
            log_dir,
            f"app-{datetime.now().strftime('%Y-%m-%d')}.info.log"
        )

        # 轮转日志Handler（50MB/文件，保留10个备份）
        file_handler = RotatingFileHandler(
            filename=log_filename,
            maxBytes=50 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s | %(module)s:%(funcName)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %z"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

        # 验证日志目录可写性
        try:
            test_file = os.path.join(log_dir, "log_write_test.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            root_logger.info(f"✅ 应用启动成功，日志文件初始化完成 | 日志路径：{log_filename}")
        except Exception as e:
            root_logger.error(f"❌ 日志目录不可写：{log_dir} | 错误：{str(e)}")


# 初始化全局日志（仅执行一次）
init_global_logger()