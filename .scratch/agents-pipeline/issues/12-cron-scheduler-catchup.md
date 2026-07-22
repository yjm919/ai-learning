# 12 — Cron 调度器 + 补采逻辑

**What to build:** 每日定时触发采集管线，以及系统恢复时自动补采所有缺失日的数据。通过 `knowledge/.state.json` 记录上次成功日期，计算缺失日期列表并逐日执行管线。

**Blocked by:** 03, 11

**Status:** ready-for-agent

- [ ] `src/scheduler.py` 实现 cron 定时器，默认每日 UTC 00:00 触发 `run_pipeline()`
- [ ] `src/scheduler.py` 实现 `run_catchup()` — 读取 `.state.json`，计算缺失日期，逐日调用 `run_pipeline(date)`
- [ ] 补采时按日期升序执行（从最早缺失日到当日）
- [ ] 每日执行成功后更新 `.state.json` 的 `last_successful_date`
- [ ] Cron 执行与补采不冲突（补采期间到达定时点则排队等待）
- [ ] 调度器 crash 后重启自动检测并补采
- [ ] 所有操作带 `trace_id` 日志
- [ ] 单元测试覆盖：补采日期计算、定时触发模拟
