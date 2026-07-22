# 08 — Organizer 审核 + Markdown 日报

**Blocked by:** 02, 07

**Status:** ready-for-agent

## What to build

读取 draft 条目，score ≥ 50 → `published`（< 50 保留 draft，error 跳过）。格式化为 Markdown 日报写入 `knowledge/daily-{YYYYMMDD}.md`。

## Acceptance Criteria

- [ ] `src/nodes/organizer.py` — LangGraph 节点函数
- [ ] score ≥ 50 的 draft → `published`；< 50 保持 `draft`
- [ ] `status=error` 条目跳过不处理
- [ ] 按评分降序 → 同分 stars 降序
- [ ] Markdown 格式：标题 + 摘要 + tags + 评分 + 链接 + 分隔线
- [ ] UTF-8 写入 `knowledge/daily-{YYYYMMDD}.md`
- [ ] 日报标题含日期、总条数、去重后条数
- [ ] 单元测试：score 分界线、error 跳过、Markdown 格式
