在 Mac 上，可以使用 Homebrew 来安装：
brew install tree

执行 tree 命令时排除特定的目录（如 docs 和 __pycache__ 和 alembic）# 用cmd+r替换‘NBSPNBSP’为4个普通空格；
((.venv) ) wutaodeMacBook-Pro:backend wutao$ tree -I 'docs|olddocs20251014|__pycache__|alembic|db.py|Dockerfile|Makefile|README.md|alembic.ini|dependencies|crud.py|initial_data.py|permission_docs.md|session.py|scripts'
