# 11 — LangGraph 状态机（全链路编排）

**Blocked by:** 05, 06, 07, 08, 09, 10

**Status:** ready-for-agent

## What to build

LangGraph 构建 `collector → analyzer → organizer` 串行状态机。定义 PipelineState、节点、条件边、错误边界。部分源失败不阻塞，部分条目失败不阻塞。

## Acceptance Criteria

- [ ] `src/graph.py` — `PipelineState` TypedDict（raw_data / articles / report_path / errors）
- [ ] StateGraph 节点：collect_github → collect_hn → analyze → organize → push_telegram → push_feishu
- [ ] 条件边：源失败 → 跳过继续；analyze 大量 error → 仍继续；推送任一失败 → 继续另一通道
- [ ] `run_pipeline(date: str | None = None) -> PipelineState`
- [ ] 全链路 ≤ 15 分钟
- [ ] 所有节点带 trace_id 日志
- [ ] 集成测试：端到端绿色路径
