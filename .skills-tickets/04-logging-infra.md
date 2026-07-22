# 04 — 日志基础设施 — trace_id + 结构化日志

**Blocked by:** None

**Status:** ready-for-agent

## What to build

全链路日志系统，每次请求携带 `trace_id`。所有模块用 `logging`（禁止 `print()`）。错误日志仅含异常堆栈，不含请求体或条目全文。

## Acceptance Criteria

- [ ] `src/logging_config.py` — `setup_logging(level=INFO)` 全局配置，格式含 timestamp + trace_id + level + message
- [ ] `src/trace.py` — `generate_trace_id() -> str`，UUID-based
- [ ] ruff 启用 `T20`（flake8-print），禁止裸 `print()`
- [ ] 错误日志不含请求体、不含知识条目全文（仅 title/summary 可记录）
- [ ] 单元测试：trace_id 生成、日志格式
