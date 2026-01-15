import sentry_sdk
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api.main import api_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    """增强路由ID生成函数，处理无tags情况"""
    if not route.tags:
        return f"untagged-{route.name}"
    return f"{route.tags[0]}-{route.name}" if route.tags else f"notag-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# 构建跨平台兼容的静态文件路径
static_dir = Path(__file__).parent / "api" / "static" / "swagger-ui"

# 确保静态文件目录存在
if not static_dir.exists():
    raise RuntimeError(f"Swagger UI静态文件目录不存在: {static_dir}")

# 挂载静态文件目录
app.mount(
    "/static/swagger-ui",
    StaticFiles(directory=str(static_dir)),
    name="swagger_static"
)


# 自定义Swagger UI路由
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon.png",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
    )

# OAuth2重定向路由
@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
