# 11 — LangGraph 状态机（全链路编排）

**What to build:** 使用 LangGraph 构建 `collector → analyzer → organizer` 的串行状态机。定义状态对象、节点流转、条件跳转和错误边界。部分源采集失败不阻塞，analyzer 部分条目失败不阻塞。

**Blocked by:** 05, 06, 07, 08, 09, 10

**Status:** ready-for-agent

- [ ] `src/graph.py` 定义 `PipelineState` TypedDict（含 raw_data, articles, report_path, errors 等字段）
- [ ] `src/graph.py` 构建 StateGraph，节点：`collect_github` → `collect_hn` → `analyze` → `organize` → `push_telegram` → `push_feishu`
- [ ] 条件边：GitHub 采集失败 → 跳过但继续 HN；HN 失败 → 跳过但继续
- [ ] 条件边：分析完成后有大量 error → 仍继续审核（organizer 跳过 error 条目）
- [ ] 条件边：推送任一失败 → 继续另一个通道，最终汇总异常
- [ ] `src/graph.py` 导出 `run_pipeline(date: str | None = None) -> PipelineState`
- [ ] 全链路 ≤ 15 分钟延迟
- [ ] 所有节点带 `trace_id` 日志
- [ ] 集成测试：完整 end-to-end 流程
