# 07 — Analyzer 节点（LLM 摘要 + 标签 + 评分 + 去重）

**What to build:** LangGraph analyzer 节点。接收 collector 原始数据，交由 LLM 对每条项目生成中文摘要、英文标签和综合评分，同日+同仓库去重后写入 `knowledge/articles/{id}.json`。不合 schema 的输出重试 3 次后落 `status=error`。

**Blocked by:** 02, 05, 06

**Status:** ready-for-agent

- [ ] `src/nodes/analyzer.py` 实现 analyzer node（LangGraph 节点函数）
- [ ] 读取 `knowledge/raw/` 下的当日 raw JSON
- [ ] 调用 LLM 生成：中文摘要 ≤ 200 字、≥ 2 个英文标签、0-100 评分
- [ ] ID 自生成，格式 `{YYYYMMDD}-{source}-{slug}`
- [ ] 同日 + 同仓库去重（GitHub 与 HN 不互斥，跨天不拦）
- [ ] LLM 输出通过 schema 校验，失败则重新提示并重试（最多 3 次）
- [ ] 3 次全部失败落 `status=error` 条目，不丢弃、不阻塞
- [ ] 全部新建条目 `status=draft`
- [ ] `analyzed_at` 设为当前 UTC 时间
- [ ] 所有操作带 `trace_id` 日志（title/summary 可记录，不记录全文）
- [ ] 单元测试覆盖：正常条目生成、去重逻辑、error 兜底
