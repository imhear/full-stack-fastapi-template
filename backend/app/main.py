"""
项目主入口文件
backend/app/main.py
上次更新：2025/12/19
# 适配改造：
# 1. 复用config.py的全局配置（ENVIRONMENT/DEFAULT_TZ），统一日志级别和时区
# 2. 适配config.py的数据库连接池配置，优化DI容器的数据库会话
# 3. 兼容config.py的SQLAlchemy日志配置，避免重复初始化日志
# 4. 保留原有所有业务逻辑、注释和功能，无破坏性修改
# 修复：移除错误的async_sessionmaker覆盖，复用deps.py的正确会话配置
# 新增：日志落文件改造，开发环境按日期+级别输出日志到文件，支持轮转
# 新增：日志落文件开关log_to_file_flag，参考Flask日志配置思路，灵活控制日志输出方式
# 优化：解决日志文件名日期占位符未替换问题，第三方库日志格式统一，启动日志request_id语义化
# 修复：移除TimedRotatingFileHandler不支持的suffix参数，解决启动TypeError
# 2025/12/19 最小化修改：适配Docker日志挂载路径/app/logs/local，确保日志落文件到指定目录
#  - 仅修改日志根目录配置，指向Docker挂载的/app/logs/local，无其他代码删减/逻辑改动
#  - 保留所有原有日志逻辑，仅调整路径变量，兼容宿主机挂载/Users/wutao/code/fastapi_demo/logs/local
# 2025/12/26 新增：422请求体校验错误处理器，打印详细字段错误信息，定位修改密码接口422问题
"""
import uuid
import logging
import os
from datetime import datetime
import sentry_sdk
from contextvars import ContextVar
from fastapi import FastAPI, Request  # 新增Request导入（异常处理器需要）
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.routing import APIRoute
# ========== 新增：导入422错误相关异常 ==========
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.openapi.utils import get_openapi  # 导入OpenAPI工具
# 导入config的全局配置
from app.core.config import settings, DEFAULT_TZ

# ====================== 新增：日志文件配置相关导入 ======================
from logging.handlers import TimedRotatingFileHandler
import traceback

from app.api import api_router
from app.di.container import Container  # 导入DI容器
# import app.core.events  # 导入事件监听器
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException
from app.core.responses import ErrorResponse
# 修复1：正确导入SQLAlchemy异常（首字母大写+驼峰命名）
from sqlalchemy.exc import IntegrityError

# ====================== 适配permission_checker.py的核心配置 ======================
# 1. 导入权限校验模块的request_id上下文变量（保持全局上下文一致）
from app.utils.permission_checker import request_id_ctx

# ====================== 新增：日志文件开关配置（参考Flask日志配置思路） ======================
# 优先级：settings配置 > 环境变量 > 默认值
# 开发环境（local）默认True（落文件），生产环境默认False（仅控制台）
try:
    # 从全局配置读取开关，无配置则走默认逻辑
    log_to_file_flag = settings.LOG_TO_FILE_FLAG
except AttributeError:
    # 环境变量控制，便于部署时灵活调整
    log_to_file_flag = os.getenv("LOG_TO_FILE_FLAG", "True") == "True" if settings.ENVIRONMENT == "local" else False

# 2. 基础日志配置（复用config的环境变量和时区，符合行业最佳实践）
def init_global_logger() -> logging.Logger:
    """初始化全局日志（复用config配置，统一时区和级别，支持日志落文件）
    行业最佳实践优化：
    - 开发环境（local）：控制台+文件输出（可通过log_to_file_flag关闭），按日期+级别拆分文件，按天轮转
    - 生产环境：默认仅控制台输出（log_to_file_flag=False），避免磁盘占用
    - 日志格式包含request_id、时区、模块、级别等核心字段
    - 自动创建日志目录，避免文件不存在错误
    灵活配置：
    - log_to_file_flag=True：日志同时输出到控制台+文件（按日期+级别拆分）
    - log_to_file_flag=False：仅输出到控制台（兼容原有逻辑）
    优化点：
    - 解决日志文件名%Y-%m-%d占位符未替换问题，生成具体日期文件名
    - 统一passlib/uvicorn等第三方库日志格式
    - 启动日志request_id语义化为app_startup
    修复点：
    - 移除TimedRotatingFileHandler不支持的suffix参数，解决启动TypeError
    2025/12/19 最小化修改：
    - 日志根目录强制指向Docker挂载路径/app/logs/local，兼容宿主机/Users/wutao/code/fastapi_demo/logs/local
    """
    # 避免重复初始化
    # 关键修改1：获取根logger（而非__name__专属logger），所有子logger都会继承
    logger = logging.getLogger()  # 原代码：logging.getLogger(__name__)
    if logger.handlers:
        return logger

    # 复用config的环境变量设置日志级别
    log_level = logging.DEBUG if settings.ENVIRONMENT == "local" else logging.INFO
    # 时区格式化（复用全局DEFAULT_TZ）
    formatter = logging.Formatter(
        "%(asctime)s | %(request_id)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z"
    )
    formatter.converter = lambda *args: datetime.now(DEFAULT_TZ).timetuple()  # 日志时间使用全局时区

    # ====================== 新增：第三方库日志统一格式 ======================
    # 适配passlib/uvicorn等第三方库日志格式，统一使用自定义处理器
    third_party_loggers = ["passlib", "uvicorn", "uvicorn.access", "uvicorn.error"]
    for logger_name in third_party_loggers:
        third_logger = logging.getLogger(logger_name)
        third_logger.setLevel(log_level)
        third_logger.handlers.clear()  # 清空默认处理器
        third_logger.propagate = True  # 传播到根日志处理器，使用自定义格式

    # ====================== 核心：日志文件开关控制 ======================
    # 1. 创建日志目录（仅当开关开启时）
    log_base_dir = None
    if log_to_file_flag:
        # 【2025/12/19 最小化修改】强制指向Docker挂载的日志目录/app/logs/local
        # 替换原有动态路径逻辑，仅修改此行，其余逻辑保留
        log_base_dir = Path("/app/logs/local")
        log_base_dir.mkdir(parents=True, exist_ok=True)
        # 最小化修改2：设置目录权限，解决Docker写入问题
        os.chmod(log_base_dir, 0o755)

    # 2. 定义日志级别映射（按级别拆分文件）
    level_map = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical"
    }

    # 3. 按开关判断是否添加文件处理器（仅local环境+开关开启时）
    file_handlers = []  # 最小化修改3：新增缓存列表，避免未定义
    if log_to_file_flag and settings.ENVIRONMENT == "local":
        # 生成当前日期（格式：YYYY-MM-DD），解决%Y-%m-%d占位符未替换问题
        current_date = datetime.now(DEFAULT_TZ).strftime("%Y-%m-%d")
        for level, level_name in level_map.items():
            # 【核心修复】直接使用固定日期文件名，不依赖轮转的suffix
            log_file_name = f"app-{current_date}.{level_name}.log"
            log_file_path = log_base_dir / log_file_name

            # 【修复】使用FileHandler替代TimedRotatingFileHandler（避免轮转干扰文件名）
            # 如需轮转，后续通过外部脚本处理，优先保证日志生成
            file_handler = logging.FileHandler(
                filename=str(log_file_path),
                mode="a",
                encoding="utf-8"
            )

            # 设置级别过滤（只处理对应级别及以上日志）
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            # 添加过滤器（注入request_id，无则显示unknown）
            class RequestIDFilter(logging.Filter):
                def filter(self, record):
                    record.request_id = request_id_ctx.get() or "unknown"
                    return True
            file_handler.addFilter(RequestIDFilter())
            # 关键修改2：添加到根logger（所有子logger都会继承）
            logger.addHandler(file_handler)
            file_handlers.append(file_handler)

            # 【调试】打印文件名生成结果，确认路径正确
            print(f"✅ 日志文件处理器已添加：{log_file_path}")

    # 4. 控制台处理器（始终保留，不受开关影响）
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)
    # 注入request_id到控制台日志
    class RequestIDFilter(logging.Filter):
        def filter(self, record):
            record.request_id = request_id_ctx.get() or "unknown"
            return True
    stream_handler.addFilter(RequestIDFilter())
    logger.addHandler(stream_handler)

    # ====================== 结束：日志文件配置 ======================

    # 全局日志配置
    logger.setLevel(log_level)
    # 关键修改3：开启根logger传播（默认True，确保子logger继承处理器）
    # 原代码：logger.propagate = False → 注释/删除这行
    # logger.propagate = False  # 注释掉这行

    # ====================== 核心修复（新增3行）：确保所有app子模块logger继承根处理器 ======================
    # 修复子模块日志无法写入文件问题，保留所有原有代码
    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()  # 清空子logger默认处理器
    app_logger.propagate = True  # 强制传播到根logger
    app_logger.setLevel(log_level)  # 统一设置级别

    # 【核心修复】强制刷新logger配置
    logging.shutdown()
    logging.basicConfig(level=log_level, handlers=logger.handlers)

    # 配置SQLAlchemy日志（避免过冗余，仅ERROR级别）
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.ERROR)
    sqlalchemy_logger.addHandler(stream_handler)
    # 仅当开关开启时，SQLAlchemy日志也落文件
    # 最小化修改4：修复file_handler未定义问题
    if log_to_file_flag and settings.ENVIRONMENT == "local" and file_handlers:
        for file_handler in file_handlers:
            sqlalchemy_logger.addHandler(file_handler)

    # 最小化修改5：强制关闭uvicorn默认处理器，确保自定义日志生效
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = []
    uvicorn_logger.propagate = True

    return logger

# 初始化全局日志
logger = init_global_logger()

# 修复2：删除无效的小写别名定义（无需此代码）
def custom_generate_unique_id(route: APIRoute) -> str:
    """增强路由ID生成函数，处理无tags情况"""
    if not route.tags:
        return f"untagged-{route.name}"
    return f"{route.tags[0]}-{route.name}" if route.tags else f"notag-{route.name}"

# Sentry初始化（复用config的配置）
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        enable_tracing=True,
        environment=settings.ENVIRONMENT  # 复用环境配置
    )

def create_app() -> FastAPI:
    # 事件监听器会自动注册，无需额外代码
    # 1. 初始化DI容器（移除错误的数据库会话覆盖，复用deps.py的配置）
    container = Container()

    # ========== 核心修复：删除错误的async_engine/async_sessionmaker覆盖代码 ==========
    # 数据库会话已由DI容器（Container）和deps.py的get_async_db统一管理
    # 无需手动创建引擎/会话工厂，避免覆盖容器原有配置

    container.wire(modules=[
        "app.api.v1.endpoints.users",  # 用户API模块（需注入Service）
        "app.api.v1.endpoints.login",  # 登录API
        "app.api.v1.endpoints.roles",  # 角色API
        "app.api.deps"  # 认证依赖模块（需注入AuthService）
    ])

    # 2. 定义OAuth2重定向URL（关键：与Swagger配置一致）
    swagger_ui_oauth2_redirect_url = "/docs/oauth2-redirect"

    # 3. 创建FastAPI应用（保留自定义Swagger配置）
    app = FastAPI(
        docs_url=None,  # 禁用默认/docs，使用自定义路由
        redoc_url=None,
        title=settings.PROJECT_NAME,  # 复用config的项目名称
        openapi_url=f"{settings.API_V1_STR}/openapi.json",  # 复用config的API前缀
        generate_unique_id_function=custom_generate_unique_id,
        swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url  # 关键：设置重定向URL
    )

    # ====================== 新增：request_id中间件（适配permission_checker.py） ======================
    @app.middleware("http")
    async def add_request_id_middleware(request: Request, call_next):
        """
        注入请求ID到上下文，支持permission_checker.py的日志上下文关联
        - 生成UUID作为request_id
        - 注入到request_id_ctx上下文变量
        - 响应头添加X-Request-ID，便于前端/运维排查
        """
        # 生成唯一request_id
        request_id = str(uuid.uuid4())
        # 注入到上下文变量（与permission_checker.py共用）
        request_id_ctx.set(request_id)
        logger.debug(f"[REQ-{request_id}] 开始处理请求 | 路径：{request.url.path} | 方法：{request.method}")

        # 处理请求
        response = await call_next(request)

        # 响应头添加request_id，便于溯源
        response.headers["X-Request-ID"] = request_id
        logger.debug(f"[REQ-{request_id}] 请求处理完成 | 状态码：{response.status_code}")

        return response

    # 4. 配置OpenAPI安全方案（核心：告诉Swagger支持OAuth2）
    # --- 关键修改：重写 custom_openapi 函数 ---
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        # 直接从config构建 Token URL（复用API前缀）
        token_url = f"{settings.API_V1_STR}/login/access-token"

        openapi_schema = get_openapi(
            title=app.title,
            version="1.0.0",
            description="FastAPI RBAC项目（支持OAuth2认证）",
            routes=app.routes,
        )

        # 添加OAuth2安全方案
        openapi_schema["components"]["securitySchemes"] = {
            "OAuth2PasswordBearer": {  # 方案名称
                "type": "oauth2",
                "flows": {  # 注意：这里是 flows，不是 flow
                    "password": {
                        "tokenUrl": token_url,  # 使用构建好的URL
                        "scopes": {}
                    }
                }
            }
        }

        # --- 关键补充：为所有需要认证的路由添加 security ---
        # 这会自动为所有依赖了reusable_oauth2的路由添加安全要求
        for path in openapi_schema["paths"].values():
            for method in path.values():
                # 检查操作是否需要认证（通过查看依赖项）
                # 这是一个简化的检查，假设认证依赖是reusable_oauth2
                if any("security" in dep or "oauth2" in str(dep).lower() for dep in method.get("security", [])):
                    method["security"] = [{"OAuth2PasswordBearer": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    # 绑定自定义OpenAPI配置
    app.openapi = custom_openapi

    # 5. 挂载静态文件（Swagger UI资源）
    static_dir = Path(__file__).parent / "api" / "static" / "swagger-ui"
    if not static_dir.exists():
        raise RuntimeError(f"Swagger UI静态文件目录不存在: {static_dir}")
    app.mount(
        "/static/swagger-ui",
        StaticFiles(directory=str(static_dir)),
        name="swagger_static"
    )

    # 6. 自定义Swagger UI路由（保留原有配置，确保oauth2_redirect_url正确）
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui/swagger-ui.css",
            swagger_favicon_url="/static/swagger-ui/favicon.png",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,  # 关键：传递重定向URL
            # 可选：默认展开认证表单（提升用户体验）
            init_oauth={
                "clientId": "swagger-ui",  # 客户端ID（非必填，仅作标识）
                "appName": app.title,
                "scopes": []
            }
        )

    # 7. OAuth2重定向路由（必须存在，否则认证后无法跳转）
    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_html()

    # 8. 配置CORS（复用config的CORS配置，确保前端可访问）
    if settings.all_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.all_cors_origins,  # 复用config的CORS配置
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

    # 修复3：AppException异常处理器修正（类名首字母大写）
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        # 异常日志关联request_id和全局时区
        request_id = request_id_ctx.get() or "unknown"
        logger.error(
            f"[REQ-{request_id}] 应用异常 | 路径：{request.url.path} | 错误码：{exc.status_code} | 详情：{exc.detail}",
            exc_info=True
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.status_code,
                message=exc.detail,
                details=None,
                request_id=request_id,  # 异常响应添加request_id，便于排查
                timestamp=datetime.now(DEFAULT_TZ).isoformat()  # 复用全局时区
            ).model_dump()
        )

    # 修复4：SQLAlchemy异常处理器使用正确的类名
    @app.exception_handler(IntegrityError)
    async def sqlalchemy_exception_handler(request: Request, exc: IntegrityError):
        # 异常日志关联request_id和全局时区
        request_id = request_id_ctx.get() or "unknown"
        logger.error(
            f"[REQ-{request_id}] 数据库完整性异常 | 路径：{request.url.path} | 详情：{str(exc)}",
            extra={"request_id": request_id},
            exc_info=True
        )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                code=400,
                message="Database integrity error",
                details=str(exc),
                request_id=request_id,  # 异常响应添加request_id，便于排查
                timestamp=datetime.now(DEFAULT_TZ).isoformat()  # 复用全局时区
            ).model_dump()
        )

    # ========== 新增：422请求体校验错误处理器（核心修改） ==========
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        处理422请求体校验错误，打印详细的字段错误信息
        - 日志包含request_id、请求路径、具体错误字段、错误原因
        - 响应格式与原有ErrorResponse保持一致，便于前端统一处理
        """
        # 获取request_id，保持日志上下文一致
        request_id = request_id_ctx.get() or "unknown"
        # 打印详细的校验错误日志（关键：定位422具体原因）
        logger.error(
            f"[REQ-{request_id}] 422请求体校验失败 | 路径：{request.url.path} | 错误详情：{exc.errors()} | 请求体：{exc.body}",
            extra={"request_id": request_id, "errors": exc.errors(), "request_body": exc.body},
            exc_info=True
        )
        # 返回标准化的错误响应
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code=422,
                message="请求参数校验失败",
                details={
                    "errors": exc.errors(),  # 具体错误列表（字段+原因）
                    "request_body": exc.body  # 原始请求体，便于排查
                },
                request_id=request_id,
                timestamp=datetime.now(DEFAULT_TZ).isoformat()
            ).model_dump()
        )

    # 9. 挂载API路由（复用config的API前缀）
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # 10. 附加容器到app.state（便于后续访问）
    app.state.container = container

    return app

# 导入全局reusable_oauth2（用于OpenAPI配置）
from app.core.security import reusable_oauth2

# 创建应用实例
app = create_app()

# 启动日志（复用config配置，包含时区）
logger.info(
    f"✅ {settings.PROJECT_NAME} 应用启动成功 | 环境：{settings.ENVIRONMENT} | API前缀：{settings.API_V1_STR} | 时区：{settings.DEFAULT_TIMEZONE} | 日志落文件开关：{log_to_file_flag}",
    extra={"request_id": "app_startup", "environment": settings.ENVIRONMENT, "timezone": settings.DEFAULT_TIMEZONE, "log_to_file_flag": log_to_file_flag}
)

# 最小化修改6：启动时验证日志目录可写性（2025/12/19 适配新路径）
if log_to_file_flag:
    try:
        # 2025/12/19 最小化修改：使用Docker挂载的日志目录
        log_dir = Path("/app/logs/local")
        test_file = log_dir / "test_permission.log"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        logger.info(f"✅ 日志目录可写性验证通过：{log_dir}", extra={"request_id": "app_startup"})

        # 【核心修复】启动时主动写入一条日志到文件，确保文件创建
        current_date = datetime.now(DEFAULT_TZ).strftime("%Y-%m-%d")
        info_log_file = log_dir / f"app-{current_date}.info.log"
        with open(info_log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(DEFAULT_TZ).strftime('%Y-%m-%d %H:%M:%S %z')} | app_startup | root | INFO | 应用启动成功，日志文件初始化完成\n")

    except Exception as e:
        logger.error(f"❌ 日志目录可写性验证失败：{log_dir} | 错误：{str(e)}", extra={"request_id": "app_startup"})