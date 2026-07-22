# 06 — Hacker News 采集器

**What to build:** 从 Hacker News API 获取 top stories（top 30），按标题关键词过滤 AI 相关条目，交 LLM 做二次相关性甄别，输出 raw JSON 到 `knowledge/raw/`。

**Blocked by:** 01, 04

**Status:** ready-for-agent

- [ ] `.opencode/skills/hacker-news.md` 存在，定义 Agent 抓取策略与输出格式
- [ ] `src/collectors/hn_api.py` 封装 HN API 调用（top stories + item details），带速率限制退避
- [ ] 标题关键词过滤：匹配 AI/LLM/Agent/ML 相关词汇
- [ ] LLM 二次相关性甄别（非 AI 相关条目剔除）
- [ ] 输出 JSON 数组写入 `knowledge/raw/hn-{YYYYMMDD}.json`
- [ ] 每条含 `title`、`url`、`points`、`description`
- [ ] HN API 超时或错误时不阻塞、不 panic
- [ ] 所有操作带 `trace_id` 日志
