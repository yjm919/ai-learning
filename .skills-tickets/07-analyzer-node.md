# 07 — Analyzer 节点

**Blocked by:** 02, 05, 06

**Status:** ready-for-agent

## What to build

LangGraph analyzer 节点。读取 raw JSON，调用 LLM 生成摘要/标签/评分，同日+同仓库去重后写 `knowledge/articles/{id}.json`。不合 schema 重试 3 次 → `status=error`。

## Acceptance Criteria

- [ ] `src/nodes/analyzer.py` — LangGraph 节点函数
- [ ] 读取当日 `knowledge/raw/` 的 raw JSON
- [ ] LLM 生成中文摘要 ≤ 200 字、≥ 2 个英文标签、0–100 评分
- [ ] ID 自生成 `{YYYYMMDD}-{source}-{slug}`
- [ ] 同日+同仓库去重（GitHub/HN 不互斥，跨天不拦）
- [ ] schema 校验失败 → 重新提示 LLM 重试，最多 3 次
- [ ] 3 次全失败落 `status=error`，不丢弃不阻塞
- [ ] 新条目初始 `status=draft`
- [ ] `analyzed_at` = 当前 UTC
- [ ] 单元测试：正常生成、去重、error 兜底
