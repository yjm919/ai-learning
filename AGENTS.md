# AGENTS.md — AI 知识库助手

## 项目概述

AI 知识库助手是一个自动化技术情报系统：定时从 GitHub Trending 和 Hacker News 采集 AI/LLM/Agent 领域的热门项目与讨论，交由 AI 进行摘要、分类和去重分析，结构化落库为 JSON 条目，最终通过 Telegram、飞书等多渠道推送给订阅者。

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
│   ├── raw/                     # 采集原始数据（Markdown / JSON）
│   └── articles/                # 分析后的结构化条目（JSON）
├── src/                         # Python 源码（LangGraph 图、工具函数等）
├── tests/                       # 单元测试
├── pyproject.toml               # 项目配置与依赖
└── .gitignore
```

## 知识条目 JSON 格式

每个分析后的知识条目存储为 `knowledge/articles/{id}.json`：

```jsonc
{
  "id": "20250720-github-langgraph-v2",       // {date}-{source}-{slug}
  "title": "LangGraph v2.0 发布",
  "source": "github",                          // github | hackernews
  "source_url": "https://github.com/langchain-ai/langgraph",
  "summary": "LangGraph 发布 v2.0，引入原生多 Agent 协作与流式图执行引擎，性能提升 3 倍。",
  "summary_en": "LangGraph v2.0 released with native multi-agent collaboration...",
  "tags": ["agent", "langgraph", "workflow", "python"],
  "status": "published",                       // draft | published | archived
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
| `id` | string | 是 | 唯一标识，格式 `{YYYYMMDD}-{source}-{slug}` |
| `title` | string | 是 | 中文标题（未翻译则为英文） |
| `source` | string | 是 | 来源：`github` 或 `hackernews` |
| `source_url` | string | 是 | 原始链接 |
| `summary` | string | 是 | 中文摘要（≤ 200 字） |
| `summary_en` | string | 否 | 英文摘要 |
| `tags` | string[] | 是 | 标签列表，不少于 2 个 |
| `status` | string | 是 | 状态：`draft` / `published` / `archived` |
| `score` | int | 否 | 综合评分 0-100，基于热度与相关性 |
| `metrics` | object | 否 | 原始量化指标（stars / points 等） |
| `fetched_at` | string | 是 | ISO 8601 采集时间 |
| `analyzed_at` | string | 否 | ISO 8601 分析完成时间 |
| `published_at` | string | 否 | ISO 8601 发布时间 |

## Agent 角色概览

| 角色 | Agent 文件 | 职责 | 触发方式 |
|------|-----------|------|----------|
| **采集 Agent** (collector) | `.opencode/agents/collector.md` | 从 GitHub Trending / HN API 拉取原始数据，写入 `knowledge/raw/` | Cron 定时 / 手动 `fetch` 命令 |
| **分析 Agent** (analyst) | `.opencode/agents/analyst.md` | 对 `knowledge/raw/` 中的条目进行摘要、打标签、评分、去重，生成结构化 JSON 写入 `knowledge/articles/` | 采集完成后自动触发 |
| **整理 Agent** (organizer) | `.opencode/agents/organizer.md` | 将 `status=draft` 的条目审核后批量设为 `published`，并按渠道（Telegram / 飞书）规则推送分发 | 手动触发 / 定时批量推送 |

## 红线（绝对禁止）

1. **禁止硬编码 API Token / Webhook URL / Secret Key**。所有敏感配置必须通过环境变量或 `.env` 文件注入，且 `.env` 须列入 `.gitignore`。
2. **禁止在知识条目 JSON 中写入非 UTF-8 编码的非法字符**，入库前必须校验编码与 JSON schema。
3. **禁止在采集阶段执行任何代码**（如对 GitHub 仓库做 `git clone` 或 `pip install`），仅允许读取公开元数据（API / RSS / 页面摘要）。
4. **禁止直接调用大模型原始 HTTP API**，必须通过 OpenCode 的统一模型适配层访问，确保模型切换不影响业务代码。
5. **禁止提交 `knowledge/raw/` 和 `knowledge/articles/` 目录下的数据文件到 Git**，这些目录已在 `.gitignore` 中排除。
6. **禁止在日志中打印知识条目全文**（title / summary 除外），防止泄密和日志膨胀。错误日志仅记录异常堆栈，不得包含请求体。
