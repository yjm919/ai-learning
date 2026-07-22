# 04 — 日志基础设施 — trace_id + 结构化日志

**What to build:** 全链路日志系统，每次请求携带可追溯的 `trace_id`。所有模块使用 `logging` 模块，禁止裸 `print()`。错误日志仅含异常堆栈，不含请求体或知识条目全文。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `src/logging_config.py` 实现 `setup_logging(level=INFO)` — 全局 logging 配置，格式含 timestamp + trace_id + level + message
- [ ] `src/trace.py` 实现 `generate_trace_id() -> str` — 生成 UUID-based trace_id
- [ ] `ruff` 规则启用 `T20`（flake8-print）禁止裸 `print()`
- [ ] 所有结构化日志带 `trace_id` 前缀
- [ ] 错误日志不包含请求体、不包含知识条目全文（仅含 title / summary）
- [ ] 单元测试验证 trace_id 生成与日志格式
