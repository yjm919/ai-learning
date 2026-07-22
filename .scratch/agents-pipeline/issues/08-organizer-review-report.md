# 08 — Organizer 审核 + Markdown 日报

**What to build:** 读取 analyzer 产出的 `draft` 条目，按 score 自动审核（≥ 50 → `published`，< 50 保留 `draft`），`status=error` 跳过。将审核后的条目格式化为 Markdown 日报并写入 `knowledge/daily-{YYYYMMDD}.md`。

**Blocked by:** 02, 07

**Status:** ready-for-agent

- [ ] `src/nodes/organizer.py` 实现 organizer node（LangGraph 节点函数）
- [ ] 读取当日 `knowledge/articles/*.json`（仅 status=draft 的条目）
- [ ] score ≥ 50 → status 设为 `published`；score < 50 → 保持 `draft`
- [ ] `status=error` 条目不参与审核，跳过
- [ ] 按评分降序 → 同分按 stars 降序排列
- [ ] Markdown 日报格式：标题 + 摘要 + tags + 评分 + 来源链接 + 分隔线
- [ ] 写入 `knowledge/daily-{YYYYMMDD}.md`，UTF-8 编码
- [ ] 日报标题行包含日期、总条数、去重后条数
- [ ] `published_at` 此时暂不设置（由推送 ticket 回填）
- [ ] 单元测试覆盖：score 分界线、error 跳过、Markdown 格式
