# 01 — 项目骨架 + pyproject.toml

**Blocked by:** None

**Status:** ready-for-agent

## What to build

建立 Python 3.12 项目骨架：`pyproject.toml` 声明全部依赖、`src/` 和 `tests/` 目录结构、ruff + mypy 质量门禁。后续所有模块可正常导入、lint、类型检查。

## Acceptance Criteria

- [ ] `pyproject.toml` 声明 Python 3.12、LangGraph、ruff、mypy 等依赖
- [ ] `src/__init__.py` 和 `tests/__init__.py` 存在
- [ ] `.gitignore` 涵盖 `__pycache__`、`.env`、`knowledge/raw/`、`knowledge/articles/`
- [ ] `ruff check` 全项目通过
- [ ] `ruff format --check` 全项目通过
- [ ] `mypy src/` 无错误
