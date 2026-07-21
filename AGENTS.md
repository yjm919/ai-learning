# AGENTS.md — AI 知识库助手

## 项目概述

AI 知识库助手是一个自动化技术情报系统：定时从 GitHub Trending 和 Hacker News 采集 AI/LLM/Agent 领域的热门项目与讨论，交由 AI 进行摘要、分类和去重分析，结构化落库为 JSON 条目，最终通过 Telegram、飞书双渠道推送给订阅者。

## 技术栈

| 层次 | 选型 |
|------|------|
| 运行时 | Python 3.12 |
| Agent 框架 | OpenCode（编排层）+ LangGraph（图/状态机层） |
| 大模型 | 国产大模型（通过 OpenCode 统一适配） |
| 分发渠道 | OpenClaw（Telegram / 飞书 Bot SDK） |

## 编码规范

- **PEP 8**：所有 Python 代码遵循 PEP 8，行宽 ≤ 120 字符。
- **命名**：变量 / 函数 / 方法统一使用 `snake_case`；类名 `PascalCase`；常量 `UPPER_SNAKE_CASE`。
- **docstring**：Google 风格（`Args:`、`Returns:`、`Raises:`），所有 public 函数必须有 docstring。
- **日志**：使用 `logging` 模块，禁止裸 `print()`。日志级别遵循：`DEBUG`（开发调试）、`INFO`（关键流程节点）、`WARNING`（可恢复异常）、`ERROR`（需人工介入）。
- **类型注解**：所有函数签名必须包含完整的类型注解，并通过 `mypy` 校验。
- **格式化**：使用 `ruff` 进行 lint 与格式化，CI 中 `ruff check && ruff format --check` 必须通过。

## 项目结构

```
.
├── AGENTS.md                    # 本文件
├── specs/
│   └── project-vision.md        # 项目愿景与边界定义
├── .opencode/
│   ├── agents/                  # Agent 角色定义（采集 / 分析 / 整理）
│   │   ├── collector.md
│   │   ├── analyst.md
│   │   └── organizer.md
│   ├── skills/                  # 可复用技能模块
│   │   ├── github-trending.md
│   │   ├── hacker-news.md
│   │   ├── feishu-push.md
│   │   └── telegram-push.md
│   ├── package.json
│   └── package-lock.json
├── knowledge/
│   ├── .state.json              # 补采状态文件（记录上次成功采集日期）
│   ├── raw/                     # 采集原始数据（Markdown / JSON）
│   └── articles/                # 分析后的结构化条目（JSON）
├── src/                         # Python 源码：LangGraph 状态机 + 工具实现 + Cron 调度器
├── utils/                       # 通用工具函数（如 GitHub API 封装）
├── tests/                       # 单元测试
├── pyproject.toml               # 项目配置与依赖
└── .gitignore
```

## 知识条目 JSON 格式

每个分析后的知识条目存储为 `knowledge/articles/{id}.json`：

```jsonc
{
  "id": "20250720-github-langgraph-v2",       // {YYYYMMDD}-{source}-{slug}，由 Agent 自生成
  "title": "LangGraph v2.0 发布",
  "source": "github",                          // github | hackernews
  "source_url": "https://github.com/langchain-ai/langgraph",
  "summary": "LangGraph 发布 v2.0，引入原生多 Agent 协作与流式图执行引擎，性能提升 3 倍。",
  "summary_en": "LangGraph v2.0 released with native multi-agent collaboration...",
  "tags": ["agent", "langgraph", "workflow", "python"],
  "status": "published",                       // draft | published | archived | error
  "score": 95,                                 // 综合评分 0-100
  "metrics": {
    "stars": 4200,
    "points": 312
  },
  "fetched_at": "2025-07-20T10:00:00Z",
  "analyzed_at": "2025-07-20T10:15:00Z",
  "published_at": "2025-07-20T10:30:00Z"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识，格式 `{YYYYMMDD}-{source}-{slug}`，由分析 Agent 自生成 |
| `title` | string | 是 | 中文标题（未翻译则为英文） |
| `source` | string | 是 | 来源：`github` 或 `hackernews` |
| `source_url` | string | 是 | 原始链接 |
| `summary` | string | 是 | 中文摘要（≤ 200 字） |
| `summary_en` | string | 否 | 英文摘要 |
| `tags` | string[] | 是 | 标签列表，不少于 2 个英文标签 |
| `status` | string | 是 | 状态：`draft` / `published` / `archived` / `error` |
| `score` | int | 否 | 综合评分 0-100，基于热度与相关性 |
| `metrics` | object | 否 | 原始量化指标（stars / points 等） |
| `fetched_at` | string | 是 | ISO 8601 采集时间 |
| `analyzed_at` | string | 否 | ISO 8601 分析完成时间 |
| `published_at` | string | 否 | ISO 8601 发布时间 |

## Agent 角色概览

### 采集 Agent (collector)

| 项 | 说明 |
|----|------|
| Agent 文件 | `.opencode/agents/collector.md` |
| 数据源 | **仅** GitHub Trending + Hacker News（v0.1 阶段） |
| GitHub 抓取策略 | 从 GitHub Trending 全量抓取（预计 ~25 条），按 repository topics 过滤：匹配 `ai` / `llm` / `agent` 任一关键词即保留 |
| HN 抓取策略 | 获取 Hacker News top stories（默认 top 30），按标题关键词过滤 AI 相关条目，再交由 LLM 做二次相关性甄别 |
| 降级策略 | GitHub 当日无匹配结果时，降级到 broader 榜单，不可报错或静默 |
| 输出 | 原始数据写入 `knowledge/raw/` |
| 触发方式 | Cron 定时 / 手动 `fetch` 命令 |

### 分析 Agent (analyst)

| 项 | 说明 |
|----|------|
| Agent 文件 | `.opencode/agents/analyst.md` |
| 动作 1 — 翻译 + 摘要 | 生成中文摘要，≤ 200 字 |
| 动作 2 — 打标签 | 每条至少 2 个英文标签 |
| 动作 3 — 去重 | **同日 + 同仓库** 视为重复，仅保留一条；GitHub 与 HN 不互斥、跨天不拦 |
| 动作 4 — 评分 | 0-100 分。评分维度参考 stars / HN points / AI 相关性权重，也可由 LLM 全权判断，不强制使用固定公式 |
| ID 生成 | Agent 自生成，格式 `{YYYYMMDD}-{source}-{slug}` |
| 落盘 | Agent 自行调工具写文件至 `knowledge/articles/{id}.json`，不依赖外层 Python 兜底 |
| 初始 status | 所有新条目 status = `draft` |
| 容错 | LLM 输出不合 schema → 重试 **3 次**，全部失败则落 `status=error` 的坏数据（不丢弃、不阻塞管线） |
| 触发方式 | 采集完成后自动触发 |

### 整理 Agent (organizer)

| 项 | 说明 |
|----|------|
| Agent 文件 | `.opencode/agents/organizer.md` |
| 审核规则 | 自动审核：**score ≥ 50** 的 `draft` 条目自动设为 `published`；score < 50 保留为 `draft`，留待人工决策 |
| 跳过规则 | `status=error` 条目不参与审核，跳过不做任何处理 |
| 推送渠道 | Telegram + 飞书 **双通道必须同时推送**。任一失败当日标注异常，不可静默丢弃 |
| 推送幂等 | `published_at` 已设置则跳过；未设置则推送并在成功后回填，崩溃重跑不重复推送 |
| 触发方式 | 分析完成后自动触发 / 定时批量推送 |

## 管线执行

### 执行顺序
Agent 严格串行执行：**collector → analyst → organizer**。前一阶段全部完成后，下一阶段才开始。

- 采集部分源失败（如 HN API 超时但 GitHub 成功）→ **不阻塞**，analyst 处理已采集到的数据。
- Analyst 部分条目重试 3 次仍失败落 `error` → **不阻塞**，organizer 跳过 `error` 条目，正常审核其他 `draft`。

### 时区
所有日期与时间戳（含 `YYYYMMDD` 中的日期、`fetched_at` / `analyzed_at` / `published_at`）统一使用 **UTC**。

### 推送幂等
Organizer 以 `published_at` 字段判定是否已推送：`published_at` 已设置则跳过，未设置则推送并在成功后回填。Organizer 崩溃重跑不会重复推送。

### 补采
状态持久化在 `knowledge/.state.json`，记录上次成功采集的日期。系统恢复时补采所有缺失日的数据。

### status 生命周期

```
                    ┌──────────┐
                    │  draft   │ ← 所有新条目初始状态
                    └────┬─────┘
              score ≥ 50 │  score < 50
                    ┌────┴─────┐
               ┌────┴─────┐    │ (保留 draft，等待人工决策)
               │published │    │
               └────┬─────┘    │
                手动清理 │      │ 手动清理
               ┌────┴──────┐   │
               │ archived  │←──┘
               └───────────┘
```

- `error` 条目（重试 3 次后仍不合 schema）不参与自动审核，留待人工处理。
- `archived` 为手动操作，用于清理老旧已发布条目。

## LangGraph 层（`src/`）

`src/` 下的 Python 代码承担三层职责：

| 层次 | 说明 |
|------|------|
| 工具实现 | 为 Agent 提供可调用的函数（如 GitHub API 封装、HN API 封装、JSON 校验、文件 I/O） |
| 状态机 | LangGraph 图定义采集 → 分析 → 整理的状态流转与条件跳转 |
| Cron 调度 | 定时触发采集管线，管理补采逻辑与延迟控制 |

Agent（`.opencode/agents/*.md`）充当自然语言决策层，通过 OpenCode 调用 `src/` 中的工具和方法完成实际工作。

## 系统边界

### 吞吐量
- 每日 35 条 raw → 产出 5–8 条 article。

### 延迟
- 全链路（采集触发 → 双通道推送发出）≤ **15 分钟**。

### 容错
- **补采**：状态持久化在 `knowledge/.state.json`，当日未采到数据 → 次日自动补采所有缺失日的数据。
- **重试**：Agent 输出不合 schema → 重试 3 次 → 全失败则落 `status=error`。
- **防崩**：GitHub API / HN API / LLM 任一超时或错误，系统不得 panic、不得丢失当日上下文。
- **速率限制**：GitHub API 触发 403 或 Retry-After 时执行退避重试，避免硬退出。
- **日志**：所有请求须带可追溯的 `trace_id`，错误日志仅记录异常堆栈，不得包含请求体。

### v0.1 阶段明确不做

| 不做的事 | 说明 |
|----------|------|
| 邮件推送 | 仅 Telegram + 飞书 |
| Web Dashboard | 输出形态仅 JSON 文件 + 频道推送 |
| 用户自定义订阅/偏好 | 所有订阅者看到同一份推送 |
| 历史趋势分析 / 同比环比 | 每日独立快照，不跨天对比 |
| Twitter / Reddit / arXiv / 公众号 | v0.1 不接入，远期可扩展 |

## 验收标准

1. **端到端**：从采集 → Agent 分析 → JSON 落盘 → 双通道推送，全流程无人干预跑通一次。
2. **Schema 合规**：Agent 输出的每一份 JSON 必须 100% 通过 schema 校验（含 UTF-8 编码、ISO 8601 时间、必填字段齐全）。
3. **推送到达**：双通道（Telegram + 飞书）任一失败即记当日异常，不可静默丢弃。
4. **防漏防线**：任何外部依赖异常时系统不得 panic，可重试、可降级、可落错误条目，但不可退出。

## 红线（绝对禁止）

1. **禁止硬编码 API Token / Webhook URL / Secret Key**。所有敏感配置必须通过环境变量或 `.env` 文件注入，且 `.env` 须列入 `.gitignore`。
2. **禁止在知识条目 JSON 中写入非 UTF-8 编码的非法字符**，入库前必须校验编码与 JSON schema。
3. **禁止在采集阶段执行任何代码**（如对 GitHub 仓库做 `git clone` 或 `pip install`），仅允许读取公开元数据（API / RSS / 页面摘要）。
4. **禁止直接调用大模型原始 HTTP API**，必须通过 OpenCode 的统一模型适配层访问，确保模型切换不影响业务代码。
5. **禁止提交 `knowledge/raw/` 和 `knowledge/articles/` 目录下的数据文件到 Git**，这些目录已在 `.gitignore` 中排除。
6. **禁止在日志中打印知识条目全文**（title / summary 除外），防止泄密和日志膨胀。错误日志仅记录异常堆栈，不得包含请求体。
