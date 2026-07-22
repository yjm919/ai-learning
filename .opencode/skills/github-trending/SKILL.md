---
name: github-trending
description: 当需要采集 GitHub 热门开源项目时使用此技能
allowed-tools: Read, Grep, Glob, WebFetch
---

# GitHub Trending 采集技能

## 使用场景

定时或手动从 GitHub Trending 采集 AI/LLM/Agent 领域的当日热门开源项目，结构化输出供下游分析 Agent 使用。

## 执行步骤

### 第 1 步：搜索热门仓库

通过 GitHub API 搜索当日热门仓库：

- 使用 `WebFetch` 访问 `https://github.com/trending?since=daily`
- 解析页面内容，提取当日 trending 仓库列表
- 若 GitHub Trending 页面无匹配结果，降级到 broader 榜单（`https://github.com/trending`）

### 第 2 步：提取信息

对每个仓库提取以下字段：

| 字段 | 说明 |
|------|------|
| `name` | 仓库全名（格式 `owner/repo`） |
| `url` | 仓库链接 |
| `stars` | Star 数量 |
| `language` | 主要编程语言 |
| `topics` | 仓库 topic 标签列表 |
| `description` | 仓库简介（原文） |

### 第 3 步：过滤

**纳入标准** — 仓库 topics 匹配 `ai` / `llm` / `agent` 任一关键词即保留。

**排除标准** — 以下类型必须剔除：
- awesome 列表（仓库名含 `awesome-` 前缀或 topics 含 `awesome-list`）
- 纯教程、课程聚合、面试题、个人笔记
- 非技术类资源合集

### 第 4 步：去重

以 `url` 为去重键，同一日内不重复出现同仓库。与历史采集不做比对（每日独立）。

### 第 5 步：撰写中文摘要

为每个条目生成中文摘要（≤ 150 字），使用公式：

> **项目名** + **做什么** + **为什么值得关注**

要求：语言简洁通顺，不直接拷贝 description 翻译，突出核心能力与技术价值。

### 第 6 步：排序取 Top 15

- 按 `stars` 降序排列
- 截取前 15 条

### 第 7 步：输出 JSON

将结果写入 `knowledge/raw/github-trending-YYYY-MM-DD.json`（日期为 UTC 当日）。

## 输出格式

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-07-21T10:00:00Z",
  "items": [
    {
      "name": "langgenius/dify",
      "url": "https://github.com/langgenius/dify",
      "summary": "Dify 是开源的 LLM 应用开发平台，内置 RAG 引擎与可视化工作流编排，支持 100+ 模型接入，已获 14 万 Star。",
      "stars": 149568,
      "language": "TypeScript",
      "topics": ["ai", "llm", "agent", "rag", "workflow"]
    }
  ]
}
```

## 注意事项

- 所有日期和时间使用 UTC 时区
- `collected_at` 为 ISO 8601 格式
- 输出 JSON 编码为 UTF-8，禁止非 UTF-8 非法字符
- 不执行任何代码（禁止 git clone / pip install）
- 所有操作带可追溯的 `trace_id`
- 当日无匹配结果时降级 broader 榜单，不可报错或静默丢弃
