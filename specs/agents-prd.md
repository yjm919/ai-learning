# AI 知识库助手 — Agents PRD

## 概述

AI 知识库助手是一个自动化技术情报系统，通过 Collector → Analyzer → Organizer 三个串行 Agent 完成从数据采集到双通道推送的全链路。每日从 GitHub Trending 采集 AI/LLM/Agent 领域热门项目，交由 AI 进行摘要、分类和评分，最终通过 Telegram + 飞书双渠道推送。

---

## Agent 1: Collector（采集 Agent）

### 数据源

| 源 | 策略 |
|---|---|
| GitHub Trending | 全量抓取（~25 条），按 repository topics 过滤：匹配 `ai` / `llm` / `agent` 任一即保留 |
| Hacker News | 获取 top stories（top 30），按标题关键词过滤 AI 相关条目，交 LLM 二次甄别 |

### 降级策略

GitHub 当日无匹配结果时，降级到 broader 榜单，不可报错或静默。

### 权限约束

- **禁止** Write、Edit、Bash（不写文件、不修改文件、不执行代码）
- 仅允许 Read、Glob、WebFetch

### 输出

| 字段 | 说明 |
|------|------|
| `title` | 原始仓库名（如 `langgenius/dify`） |
| `url` | GitHub 仓库链接 |
| `stars` | Star 数 |
| `description` | 仓库简介（原文） |
| `topics` | topic 标签列表 |

- 排序：按 stars 降序
- 过滤：排除纯教程、课程聚合、个人笔记
- 数量：Top 10
- 格式：JSON 数组

### 验收标准

- 条目数 ≤ 10 条
- 全部 topics 包含 `ai` / `llm` / `agent` 至少一个
- stars 为真实数字
- 无重复 URL

---

## Agent 2: Analyzer（分析 Agent）

### 核心动作

| 动作 | 说明 |
|------|------|
| 翻译 + 摘要 | 中文摘要 ≤ 200 字 |
| 打标签 | 每条 ≥ 2 个英文标签 |
| 去重 | 同日 + 同仓库视为重复，仅保留一条；GitHub 与 HN 不互斥，跨天不拦 |
| 评分 | 0–100 分，维度参考 stars / HN points / AI 相关性权重，可由 LLM 全权判断 |
| ID 生成 | 格式 `{YYYYMMDD}-{source}-{slug}`，Agent 自生成 |
| 落盘 | 写文件至 `knowledge/articles/{id}.json` |

### 知识条目 JSON Schema

```jsonc
{
  "id": "20250720-github-langgraph-v2",
  "title": "LangGraph v2.0 发布",
  "source": "github",                          // github | hackernews
  "source_url": "https://github.com/langchain-ai/langgraph",
  "summary": "...",                             // 中文摘要 ≤ 200 字
  "summary_en": "...",                          // 英文摘要
  "tags": ["agent", "langgraph"],               // ≥ 2 个英文标签
  "status": "draft",                            // 初始 status = draft
  "score": 95,                                  // 0-100
  "metrics": { "stars": 4200, "points": 312 },
  "fetched_at": "2025-07-20T10:00:00Z",        // ISO 8601, UTC
  "analyzed_at": "2025-07-20T10:15:00Z",
  "published_at": null
}
```

### 权限约束

- **禁止** Write、Edit、Bash（Agent 不写文件，落盘由管线接管）
- 仅允许 Read、WebFetch

### 容错

- LLM 输出不合 schema → 重试 3 次
- 全部失败 → 落 `status=error` 的坏数据，不丢弃、不阻塞管线

### 验收标准

- 全量覆盖 collector 输出，无遗漏
- 每条 summary ≤ 200 字，中文通顺
- 每条 tags ≥ 2 个英文标签
- 评分区分度合理
- 输出 JSON 100% 通过 schema 校验（UTF-8 编码、ISO 8601 时间、必填字段齐全）

---

## Agent 3: Organizer（整理 Agent）

### 核心动作

| 动作 | 说明 |
|------|------|
| 审核 | score ≥ 50 的 `draft` → `published`；score < 50 保留 `draft`；`error` 跳过 |
| 推送 | Telegram + 飞书双通道必须同时推送 |
| 幂等 | `published_at` 已设置则跳过；未设置则推送后回填 |
| 格式化 | 生成 Markdown 日报 |

### 推送格式

```markdown
# AI 知识日报 — 2026-07-21
> 采集自 GitHub Trending，共 10 条，去重后 10 条。

## 1. Dify — ⭐ 149,568
**标签** `llm` `agent` `rag`
**评分** 9/10
LLM 应用开发平台...
🔗 https://github.com/langgenius/dify
```

### 权限约束

- 允许 Read、Glob、Write（写入日报文件）
- **禁止** WebFetch、Bash

### 容错

- Telegram + 飞书任一失败 → 标注当日异常，不可静默丢弃
- Organizer 崩溃重跑 → 幂等，不重复推送

### 验收标准

- 日报 Markdown 格式正确，链接可点击
- 按评分降序排列，无重复条目
- 文件编码 UTF-8
- 推送到达双通道，任一失败记异常

---

## 管线执行

### 执行顺序

Collector → Analyzer → Organizer，严格串行。

### 容错策略

| 场景 | 行为 |
|------|------|
| 部分源失败（如 HN API 超时但 GitHub 成功） | 不阻塞，处理已采集数据 |
| Analyzer 部分条目重试3次仍失败 | 落 `error`，不阻塞 |
| Organizer 审核 `error` 条目 | 跳过，不处理 |

### 时区

所有日期与时间戳（`YYYYMMDD`、`fetched_at`、`analyzed_at`、`published_at`）统一使用 **UTC**。

### 补采

状态持久化在 `knowledge/.state.json`，记录上次成功采集日期。系统恢复时补采所有缺失日数据。

### 延迟要求

全链路（采集触发 → 双通道推送发出）≤ **15 分钟**。

---

## 技术栈

| 层次 | 选型 |
|------|------|
| 运行时 | Python 3.12 |
| Agent 框架 | OpenCode（编排层）+ LangGraph（图/状态机层） |
| 大模型 | 国产大模型（通过 OpenCode 统一适配） |
| 分发渠道 | Telegram Bot API + 飞书 Bot Webhook |

---

## 需要构建的内容

### 基础设施

1. **Python 项目骨架** — `pyproject.toml`、`src/`、`tests/` 目录结构与依赖
2. **知识条目 JSON Schema** — JSON Schema 定义与校验函数
3. **状态管理** — `knowledge/.state.json` 读写与补采日期计算
4. **日志与 trace_id** — 全链路请求追踪

### 工具函数

5. **GitHub Trending 采集器** — 抓取 Trending 页面，提取仓库元数据
6. **Hacker News 采集器** — 获取 top stories，关键词过滤
7. **Telegram 推送工具** — Markdown 消息推送
8. **飞书推送工具** — 富文本消息推送

### LangGraph 管线

9. **Collector 节点** — 调用采集工具，输出原始数据
10. **Analyzer 节点** — 调用 LLM 分析，输出结构化条目
11. **Organizer 节点** — 审核、推送、写日报
12. **状态机编排** — 节点串行调度、条件跳转、错误处理

### Agent 技能

13. **GitHub Trending Skill** — Agent 用 WebFetch 调用 skill 指导抓取
14. **Hacker News Skill** — Agent 用 WebFetch 调用 skill 指导抓取
15. **Telegram Push Skill** — Organizer 推送技能
16. **飞书 Push Skill** — Organizer 推送技能

### Cron 调度

17. **定时触发** — 每日定时启动采集管线
18. **补采逻辑** — 检测缺失日期并自动补采
