# AI 知识库 · 项目愿景 v1.0

## 要做什么

### 采集
- 每天从 **GitHub Trending** 全量抓取（约 35 条 raw），按 repository topics 过滤：
  关键词 `ai` / `llm` / `agent`，匹配任一即保留。
- 当日无匹配结果时，**降级到 broader 榜单**（不报错、不静默）。
- 数据源：仅 GitHub Trending + Hacker News（v0.1 阶段）。

### 分析（Agent 完成）
1. **翻译 + 摘要**（中文 ≤ 200 字）
2. **打标签**（≥ 2 个英文标签）
3. **去重**（同一天同一仓库不重复出现；GitHub 与 HN 不互斥，跨天不拦）
4. **评分**（0-100，评分维度 stars / HN points / AI 相关性权重，也可由 LLM 全权判断，不强制公式）

### 输出
- 每条输出为 **JSON 文件**，落盘 `knowledge/articles/{id}.json`。
- `id` 由 Agent 自生成，格式 `{YYYYMMDD}-{source}-{slug}`。
- Agent 自行调工具写文件，不依赖外层 Python 兜底。
- `status` 初始为 `draft`；Organizer Agent 自动审核，**score ≥ 50 自动设为 `published`**。

## 不做什么（v0.1 阶段）

| 不做的事 | 说明 |
|----------|------|
| 邮件推送 | 仅 Telegram + 飞书 |
| Web Dashboard | 输出形态仅 JSON 文件 + 频道推送 |
| 用户自定义订阅/偏好 | 所有订阅者看到同一份推送 |
| 历史趋势分析 / 同比环比 | 每日独立快照，不跨天对比 |
| Twitter / Reddit / arXiv / 公众号 | v0.1 不接入，远期可扩展 |

## 边界 & 验收

### 吞吐量
- 每日 35 条 raw → 产出 5–8 条 article。

### 延迟
- 全链路（采集触发 → 推送发出）≤ **15 分钟**。

### 容错
- 当日未采到 → **次日补采**。
- Agent 输出不合 schema → **重试 3 次**，全部失败则落 `status=error` 的坏数据（不丢弃、不阻塞管线）。
- GitHub API / HN API / LLM 任一超时或错误，系统不崩、不丢当日上下文，日志需带可追溯的 `trace_id`。

### 推送
- Telegram + 飞书双通道必须同时成功推送；任一失败当日标注异常。

## 怎么验证

1. **端到端**：从采集 → Agent 分析 → JSON 落盘 → 双通道推送，全流程无人干预跑通一次。
2. **Schema 合规**：Agent 输出的每一份 JSON 必须 100% 通过 schema 校验（含 UTF-8 编码、ISO 8601 时间、必填字段齐全）。
3. **推送到达**：双通道任一失败即记当日异常，不可静默丢弃。
4. **防漏防线**：任何外部依赖异常时系统不得 panic，可重试、可降级、可落错误条目，但不可退出。
