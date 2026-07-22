# 01 — 项目骨架 + pyproject.toml

**What to build:** 建立 Python 3.12 项目骨架，包括依赖管理、源码目录、测试目录和代码质量工具配置，使后续所有模块可正常导入、lint、类型检查。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `pyproject.toml` 存在，声明 Python 3.12、LangGraph、ruff、mypy 等依赖
- [ ] `src/` 目录存在，含 `__init__.py`
- [ ] `tests/` 目录存在，含 `__init__.py`
- [ ] `.gitignore` 涵盖 `__pycache__`、`.env`、`knowledge/raw/`、`knowledge/articles/`
- [ ] `ruff check && ruff format --check` 可通过
- [ ] `mypy src/` 可通过（即使 src/ 暂时为空）
