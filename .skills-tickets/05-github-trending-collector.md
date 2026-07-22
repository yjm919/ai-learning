# 05 — GitHub Trending 采集器

**Blocked by:** 01, 04

**Status:** ready-for-agent

## What to build

Agent 通过 WebFetch 抓取 GitHub Trending 页面，按 `ai`/`llm`/`agent` topic 过滤，取 Top 10（stars 降序），输出 raw JSON 到 `knowledge/raw/`。排杂（教程、笔记）、降级（broader 榜单）。

## Acceptance Criteria

- [ ] `.opencode/skills/github-trending.md` — Agent 抓取策略与输出格式
- [ ] Agent 通过 WebFetch 获取 GitHub Trending 内容
- [ ] topic 过滤：`ai` / `llm` / `agent` 任一命中保留
- [ ] 无匹配时降级 broader 榜单，不报错不静默
- [ ] 排除纯教程、课程聚合、个人笔记
- [ ] stars 降序 Top 10
- [ ] 输出 `knowledge/raw/github-trending-{YYYYMMDD}.json`，字段：title / url / stars / description / topics
- [ ] 带 trace_id 日志
