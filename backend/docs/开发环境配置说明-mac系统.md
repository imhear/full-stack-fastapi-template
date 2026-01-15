# 开发环境配置说明-mac系统
Author:Wu Tao  
Status:Active  
Type:Informational  
Created:2025-09-17  
Post-History:2026-01-15 

## 前置条件
### mac系统
```
1.github克隆上游代码仓库：full-stack-fastapi-template，为自己master，并建立develop分支
2.mac电脑生成ssh密钥，复制公钥内容，在GitHub后端设置中新增配置1个ssh公钥，可配多个
3.git检出项目代码到mac目录/Users/wutao/code/：git clone -b develop git@github.com:imhear/full-stack-fastapi-template.git  
4.IDE中，右键/Users/wutao/code/full-stack-fastapi-template/backend -> Mark Directory As -> Sources Root  
5.下载并安装mac版数据库软件:终端中先安装Homebrew，再使用Homebrew安装PostgreSQL服务
6.确认已上一步附带安装可视化数据库操作软件:pgAdmin 4（首次打开设置超级管理员密码，后面要用）
7.下载并安装IDE：PyCharm 2024.3.4 (Community Edition)  
8.下载并安装python：python-3.12.10
```

## 第1步：新建虚拟环境并激活
### pycharm命令行中
```pycharm命令行中
The default interactive shell is now zsh.
To update your account to use zsh, please run `chsh -s /bin/zsh`.
For more details, please visit https://support.apple.com/kb/HT208050.
wutaodeMacBook-Pro:full-stack-fastapi-template wutao$ cd backend/
wutaodeMacBook-Pro:backend wutao$ python3 -V
Python 3.12.10
wutaodeMacBook-Pro:backend wutao$ pwd
/Users/wutao/code/full-stack-fastapi-template/backend
wutaodeMacBook-Pro:backend wutao$ python3 -m venv .venv
wutaodeMacBook-Pro:backend wutao$ source .venv/bin/activate
((.venv) ) wutaodeMacBook-Pro:backend wutao$ python3 -V
Python 3.12.10
((.venv) ) wutaodeMacBook-Pro:backend wutao$ python -V
Python 3.12.10
((.venv) ) wutaodeMacBook-Pro:backend wutao$ deactivate 
wutaodeMacBook-Pro:backend wutao$ 
```

### 在IDE中，为项目配置新python解释器
PyCharm - Settings - Project:full-stack-fastapi-template - Python Interpreter - Add Interpreter - Add Local Interpreter - 解释器选择：/Users/wutao/code/full-stack-fastapi-template/backend/.venv/Scripts/python.exe - Apply - OK

## 第2步：Python虚拟环境中使用阿里源配置Poetry并安装依赖
### python虚拟环境中
```python虚拟环境中
# 1.使用阿里云镜像安装Poetry
((.venv) ) wutaodeMacBook-Pro:full-stack-fastapi-template wutao$ cd backend/
((.venv) ) wutaodeMacBook-Pro:backend wutao$ pip install poetry -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
#  2.升级pip到最新版本
[notice] A new release of pip is available: 25.0.1 -> 25.3
[notice] To update, run: pip install --upgrade pip
((.venv) ) wutaodeMacBook-Pro:backend wutao$  pip install --upgrade pip
Successfully installed pip-25.3
# 3.配置Poetry默认使用阿里源
((.venv) ) wutaodeMacBook-Pro:backend wutao$  poetry config repositories.aliyun https://mirrors.aliyun.com/pypi/simple/
((.venv) ) wutaodeMacBook-Pro:backend wutao$  poetry config virtualenvs.in-project true  # 推荐：将虚拟环境创建在项目内
((.venv) ) wutaodeMacBook-Pro:backend wutao$  poetry config installer.max-workers 10  # 加速安装
4.安装依赖
((.venv) ) wutaodeMacBook-Pro:backend wutao$  poetry install # 时间较久
Updating dependencies
Resolving dependencies... (118.5s)

Package operations: 48 installs, 0 updates, 0 removals

  - Installing mdurl (0.1.2)
  - Installing markdown-it-py (4.0.0)
  - Installing pygments (2.19.2)
  - Installing annotated-types (0.7.0)
  - Installing click (8.3.1)
  - Installing httptools (0.7.1)
  - Installing pydantic-core (2.41.5)
  - Installing python-dotenv (1.2.1)
  - Installing pyyaml (6.0.3)
  - Installing rich (14.2.0)
  - Installing typing-inspection (0.4.2)
  - Installing uvloop (0.22.1)
  - Installing watchfiles (1.1.1)
  - Installing websockets (16.0)
  - Installing cachetools (6.2.4)
  - Installing cssselect (1.3.0)
  - Installing cssutils (2.11.1)
  - Installing dnspython (2.8.0)
  - Installing greenlet (3.3.0)
  - Installing lxml (6.0.2)
  - Installing markupsafe (3.0.3)
  - Installing pydantic (2.12.5)
  - Installing rich-toolkit (0.17.1)
  - Installing six (1.17.0)
  - Installing starlette (0.46.2)
  - Installing typer (0.21.1)
  - Installing uvicorn (0.40.0)
  - Installing bcrypt (4.3.0): Downloading... 0%
  - Installing bcrypt (4.3.0): Downloading... 10%
  - Installing chardet (5.2.0): Downloading... 20%
  - Installing bcrypt (4.3.0): Downloading... 20%
  - Installing bcrypt (4.3.0): Downloading... 30%
  - Installing bcrypt (4.3.0): Downloading... 40%
  - Installing bcrypt (4.3.0): Downloading... 50%
  - Installing bcrypt (4.3.0): Downloading... 60%
  - Installing bcrypt (4.3.0): Downloading... 70%
  - Installing bcrypt (4.3.0): Downloading... 80%
  - Installing bcrypt (4.3.0): Downloading... 90%
  - Installing bcrypt (4.3.0): Downloading... 100%
  - Installing bcrypt (4.3.0): Installing...
  - Installing bcrypt (4.3.0)
  - Installing chardet (5.2.0)
  - Installing email-validator (2.3.0)
  - Installing fastapi (0.115.14)
  - Installing fastapi-cli (0.0.7)
  - Installing jinja2 (3.1.6)
  - Installing mako (1.3.10)
  - Installing premailer (3.10.0)
  - Installing psycopg-binary (3.3.2)
  - Installing python-dateutil (2.9.0.post0)
  - Installing python-multipart (0.0.21)
  - Installing sqlalchemy (2.0.45)
  - Installing alembic (1.18.1)
  - Installing emails (0.6)
  - Installing passlib (1.7.4)
  - Installing psycopg (3.3.2)
  - Installing pydantic-settings (2.12.0)
  - Installing pyjwt (2.10.1)
  - Installing sentry-sdk (1.45.1)
  - Installing sqlmodel (0.0.31)
  - Installing tenacity (8.5.0)

Writing lock file

Installing the current project: app (0.1.0)
```

## 第3步：配置数据库连接参数并创建数据库实体
### IDE中，环境配置文件：/Users/wutao/code/full-stack-fastapi-template/.env
```python配置文件
# Backend
BACKEND_CORS_ORIGINS="http://localhost,http://localhost:5173,https://localhost,https://localhost:5173,http://localhost.tiangolo.com"
SECRET_KEY=改成你自己的密钥
FIRST_SUPERUSER=改成你自己的超级管理员账号,邮箱格式
FIRST_SUPERUSER_PASSWORD=改成你自己的超级管理员密码

# Postgres
POSTGRES_SERVER=改成你自己的数据库实例所在服务器ip
POSTGRES_PORT=改成你自己的数据库连接端口号
POSTGRES_DB=改成你自己的数据库实例名称
POSTGRES_USER=改成你自己的数据库连接账号
POSTGRES_PASSWORD=改成你自己的数据库连接密码
```

### 启动 PostgreSQL 服务
```终端中，使用 Homebrew 启动 PostgreSQL 服务，因为之前切换到docker启动，文件权限可能需要重新设置
Last login: Thu Jan 15 21:38:37 on ttys001
wutao@wutaodeMacBook-Pro ~ % brew services stop postgresql@14
Stopping `postgresql@14`... (might take a while)
==> Successfully stopped `postgresql@14` (label: homebrew.mxcl.postgresql@14)
wutao@wutaodeMacBook-Pro ~ % pkill -f postgres || true
wutao@wutaodeMacBook-Pro ~ % sudo chown -R $(whoami) /usr/local/var/postgresql@14
Password:
wutao@wutaodeMacBook-Pro ~ % chmod -R 700 /usr/local/var/postgresql@14
wutao@wutaodeMacBook-Pro ~ % pg_ctl -D /usr/local/var/postgresql@14 start # brew services依赖launchctl易出假反馈，直接用 PostgreSQL 原生命令pg_ctl启动，能看到具体失败原因
pg_ctl: another server might be running; trying to start server anyway
waiting for server to start....2026-01-15 21:53:28.945 CST [52547] LOG:  starting PostgreSQL 14.19 (Homebrew) on x86_64-apple-darwin23.6.0, compiled by Apple clang version 16.0.0 (clang-1600.0.26.6), 64-bit
2026-01-15 21:53:28.946 CST [52547] LOG:  listening on IPv6 address "::1", port 5432
2026-01-15 21:53:28.946 CST [52547] LOG:  listening on IPv4 address "127.0.0.1", port 5432
2026-01-15 21:53:28.947 CST [52547] LOG:  listening on Unix socket "/tmp/.s.PGSQL.5432"
2026-01-15 21:53:28.952 CST [52548] LOG:  database system was interrupted; last known up at 2025-10-29 19:48:50 CST
2026-01-15 21:53:29.034 CST [52548] LOG:  database system was not properly shut down; automatic recovery in progress
2026-01-15 21:53:29.040 CST [52548] LOG:  redo starts at 0/1A637F8
2026-01-15 21:53:29.040 CST [52548] LOG:  invalid record length at 0/1A638E0: wanted 24, got 0
2026-01-15 21:53:29.040 CST [52548] LOG:  redo done at 0/1A638A8 system usage: CPU: user: 0.00 s, system: 0.00 s, elapsed: 0.00 s
2026-01-15 21:53:29.051 CST [52547] LOG:  database system is ready to accept connections
 done
server started
wutao@wutaodeMacBook-Pro ~ % createdb admin_panel_2026 # 创建数据库
wutao@wutaodeMacBook-Pro ~ % psql -d admin_panel_2026 # 验证数据库是否创建成功
psql (14.19 (Homebrew))
Type "help" for help.

admin_panel_2026=# # 进入 `admin_panel_2026=#` 提示符即成功，退出用 \q
```

### 创建数据库实体
```终端中，使用 Homebrew 默认方式创建数据库
# 直接使用 createdb 命令（无需 sudo）
wutao@wutaodeMacBook-Pro ~ % createdb admin_panel_2026
wutao@wutaodeMacBook-Pro ~ % psql -d admin_panel_2026
psql (14.19 (Homebrew))
Type "help" for help.

admin_panel_2026=# 
```

## 第4步：使用alembic初始化数据库表结构

### python虚拟环境中
#### 情况一：如果这是全新项目且数据库为空
```python虚拟环境中
The default interactive shell is now zsh.
To update your account to use zsh, please run `chsh -s /bin/zsh`.
For more details, please visit https://support.apple.com/kb/HT208050.
((.venv) ) wutaodeMacBook-Pro:full-stack-fastapi-template wutao$ cd backend/
((.venv) ) wutaodeMacBook-Pro:backend wutao$ alembic stamp head # 标记当前数据库为最新版本
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running stamp_revision  -> 1a31ce608336
((.venv) ) wutaodeMacBook-Pro:backend wutao$ alembic revision --autogenerate -m "init_db_20260115"
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.schemas
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.tables
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
INFO  [alembic.autogenerate.compare.tables] Detected added table 'user'
INFO  [alembic.autogenerate.compare.constraints] Detected added index 'ix_user_email' on '('email',)'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'item'
  Generating /Users/wutao/code/full-stack-fastapi-template/backend/app/alembic/versions/ef947c38d184_init_db_20260115.py ...  done
((.venv) ) wutaodeMacBook-Pro:backend wutao$ alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 1a31ce608336 -> ef947c38d184, init_db_20260115
((.venv) ) wutaodeMacBook-Pro:backend wutao$ 
```

## 第5步：使用脚本文件创建超级管理员账号，实际上不是超级管理员
### python虚拟环境中
```python虚拟环境中
# 如果偷懒拷贝了上个项目的虚拟环境配置文件，那么请参考：backend/docs/bugs/在新目录下运行脚本，但 Python 解释器却加载了旧目录中的代码.md

The default interactive shell is now zsh.
To update your account to use zsh, please run `chsh -s /bin/zsh`.
For more details, please visit https://support.apple.com/kb/HT208050.
((.venv) ) wutaodeMacBook-Pro:full-stack-fastapi-template wutao$ cd backend/
((.venv) ) wutaodeMacBook-Pro:backend wutao$ python app/initial_data.py 
INFO:__main__:Creating initial data
WARNING:passlib.handlers.bcrypt:(trapped) error reading bcrypt version
Traceback (most recent call last):
  File "/Users/wutao/code/full-stack-fastapi-template/backend/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 620, in _load_backend_mixin
    version = _bcrypt.__about__.__version__
              ^^^^^^^^^^^^^^^^^
AttributeError: module 'bcrypt' has no attribute '__about__'
INFO:__main__:Initial data created
((.venv) ) wutaodeMacBook-Pro:backend wutao$ 
```

## 第6步：启动fastapi后端项目
### python虚拟环境中
```python虚拟环境中
The default interactive shell is now zsh.
To update your account to use zsh, please run `chsh -s /bin/zsh`.
For more details, please visit https://support.apple.com/kb/HT208050.
((.venv) ) wutaodeMacBook-Pro:backend wutao$ pwd
/Users/wutao/code/full-stack-fastapi-template/backend
((.venv) ) wutaodeMacBook-Pro:backend wutao$ uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
INFO:     Will watch for changes in these directories: ['/Users/wutao/code/full-stack-fastapi-template/backend']
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [52935] using WatchFiles
INFO:     Started server process [52940]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 开发环境配置完成，现在可以开发你自己的功能了

## 扩展：设置swagger文档依赖项为本地资源

### IDE中，新建目录：backend/app/api/static/swagger-ui
下载3个文件拷贝到该目录下：favicon.png、swagger-ui.css、swagger-ui-bundle.js

### IDE中，修改应用入口文件：backend/app/main.py
```python
# backend/app/main.py

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

# Sentry初始化
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
        # allow_origins=settings.all_cors_origins,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
```

### git常用命令
```python虚拟环境中
The default interactive shell is now zsh.
To update your account to use zsh, please run `chsh -s /bin/zsh`.
For more details, please visit https://support.apple.com/kb/HT208050.
((.venv) ) wutaodeMacBook-Pro:full-stack-fastapi-template wutao$ cd backend/
# 1. 查看修改的文件
((.venv) ) wutaodeMacBook-Pro:backend wutao$ git status
On branch develop
Your branch is up to date with 'origin/develop'.

Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        new file:   app/api/static/swagger-ui/favicon.png
        new file:   app/api/static/swagger-ui/swagger-ui-bundle.js
        new file:   app/api/static/swagger-ui/swagger-ui.css

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   ../.env
        modified:   ../.gitignore
        modified:   app/main.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
        ../.idea/
        app/alembic/versions/ef947c38d184_init_db_20260115.py
        docs/
        poetry.lock
# 2. 添加所有修改的文件到暂存区（也可指定单个文件：git add 文件名）
((.venv) ) wutaodeMacBook-Pro:backend wutao$ git add .
# 3. 提交暂存区的文件到本地仓库（备注需清晰）
((.venv) ) wutaodeMacBook-Pro:backend wutao$ git commit -m "备注信息：初始化项目，新增gitignore拦截文件类型，本地加载swagger文档依赖"
[develop 4866785] 备注信息：初始化项目，新增gitignore拦截文件类型，本地加载swagger文档依赖
 7 files changed, 2605 insertions(+), 1 deletion(-)
 create mode 100644 backend/app/alembic/versions/ef947c38d184_init_db_20260115.py
 create mode 100644 backend/app/api/static/swagger-ui/favicon.png
 create mode 100644 backend/app/api/static/swagger-ui/swagger-ui-bundle.js
 create mode 100644 backend/app/api/static/swagger-ui/swagger-ui.css
 create mode 100644 "backend/docs/\345\274\200\345\217\221\347\216\257\345\242\203\351\205\215\347\275\256\350\257\264\346\230\216-mac\347\263\273\347\273\237.md"
 create mode 100644 backend/poetry.lock
# 4. 推送本地 develop 分支到远程 GitHub 的 develop 分支
((.venv) ) wutaodeMacBook-Pro:backend wutao$ git push origin develop
Enumerating objects: 24, done.
Counting objects: 100% (24/24), done.
Delta compression using up to 16 threads
Compressing objects: 100% (16/16), done.
Writing objects: 100% (17/17), 506.61 KiB | 1.44 MiB/s, done.
Total 17 (delta 6), reused 1 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (6/6), completed with 6 local objects.
To github.com:imhear/full-stack-fastapi-template.git
   63f167d..4866785  develop -> develop
((.venv) ) wutaodeMacBook-Pro:backend wutao$
```