# 03 — 状态管理 — .state.json 读写 + 补采日期计算

**What to build:** 持久化系统运行状态，记录上次成功采集日期。系统启动或恢复时自动计算缺失日期列表，供补采逻辑使用。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `src/state.py` 实现 `read_state() -> dict` — 读取 `knowledge/.state.json`，文件不存在则返回默认值 `{"last_successful_date": null}`
- [ ] `src/state.py` 实现 `write_state(state: dict) -> None` — 原子写入 `knowledge/.state.json`
- [ ] `src/state.py` 实现 `get_missed_dates() -> list[str]` — 从 `last_successful_date` 次日到今天的 UTC 日期列表（YYYYMMDD 格式）
- [ ] `src/state.py` 实现 `mark_date_successful(date: str) -> None` — 更新 `last_successful_date`
- [ ] 单元测试覆盖：首次运行（无 .state.json）、正常补采日期计算、连续多日缺失
