# 06 — Hacker News 采集器

**Blocked by:** 01, 04

**Status:** ready-for-agent

## What to build

Agent 调用 HN API 获取 top 30，标题关键词过滤后交 LLM 二次甄别，输出 raw JSON 到 `knowledge/raw/`。

## Acceptance Criteria

- [ ] `.opencode/skills/hacker-news.md` — Agent 抓取策略与输出格式
- [ ] `src/collectors/hn_api.py` — HN API 调用（top stories + item details），带速率限制退避
- [ ] 标题关键词过滤 AI/LLM/Agent/ML 相关条目
- [ ] LLM 二次相关性甄别剔除不相关条目
- [ ] 输出 `knowledge/raw/hn-{YYYYMMDD}.json`，字段：title / url / points / description
- [ ] HN API 超时/错误不 panic，不阻塞管线
- [ ] 带 trace_id 日志
