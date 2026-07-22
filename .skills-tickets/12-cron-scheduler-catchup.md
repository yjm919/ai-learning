# 12 — Cron 调度器 + 补采逻辑

**Blocked by:** 03, 11

**Status:** ready-for-agent

## What to build

每日 UTC 00:00 触发 `run_pipeline()`；系统恢复时自动补采所有缺失日数据。通过 `.state.json` 记录状态。

## Acceptance Criteria

- [ ] `src/scheduler.py` — cron 定时器，默认每日 UTC 00:00 触发
- [ ] `run_catchup()` — 读 `.state.json` 计算缺失日期，逐日调用 `run_pipeline(date)`（升序）
- [ ] 每日成功后更新 `last_successful_date`
- [ ] 补采期间到达定时点 → 排队等待，不冲突
- [ ] 调度器 crash 重启 → 自动检测补采
- [ ] 带 trace_id 日志
- [ ] 单元测试：补采日期计算、定时触发模拟
