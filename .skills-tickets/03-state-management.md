# 03 — 状态管理 — .state.json 读写 + 补采日期计算

**Blocked by:** None

**Status:** ready-for-agent

## What to build

`knowledge/.state.json` 读写模块，记录上次成功采集日期。系统启动/恢复时自动计算缺失日期列表，供 scheduler 补采使用。

## Acceptance Criteria

- [ ] `src/state.py` — `read_state() -> dict`，文件不存在返回 `{"last_successful_date": null}`
- [ ] `src/state.py` — `write_state(state: dict) -> None`，原子写入
- [ ] `src/state.py` — `get_missed_dates() -> list[str]`，从 last_successful_date 次日到今天（UTC YYYYMMDD）
- [ ] `src/state.py` — `mark_date_successful(date: str) -> None`
- [ ] 单元测试：首次运行（无 .state.json）、正常补采日期、连续多日缺失
