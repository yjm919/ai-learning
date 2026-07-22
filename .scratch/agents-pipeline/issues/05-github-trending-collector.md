# 05 — GitHub Trending 采集器

**What to build:** 从 GitHub Trending 页面全量抓取当日仓库列表，按 `ai`/`llm`/`agent` topic 关键词过滤，取 Top 10 按 stars 降序输出 raw JSON 到 `knowledge/raw/`。当日无匹配结果时降级到 broader 榜单。

**Blocked by:** 01, 04

**Status:** ready-for-agent

- [ ] `.opencode/skills/github-trending.md` 存在，定义 Agent 抓取策略与输出格式
- [ ] Agent 通过 WebFetch 获取 GitHub Trending 页面内容
- [ ] 按 repository topics 过滤：匹配 `ai` / `llm` / `agent` 任一即保留
- [ ] 当日无匹配时降级到 broader 榜单（不报错、不静默）
- [ ] 排除纯教程、课程聚合、个人笔记
- [ ] 按 stars 降序，取 Top 10
- [ ] 输出 JSON 数组写入 `knowledge/raw/github-trending-{YYYYMMDD}.json`
- [ ] 每条含 `title`、`url`、`stars`、`description`、`topics`
- [ ] 所有操作带 `trace_id` 日志
