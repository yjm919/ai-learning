---
name: github-trending
description: >
  GitHub Trending 采集：抓取每日热门仓库，按 AI/LLM/Agent 关键词过滤。
  触发条件 —— 用户浏览/采集/抓取 GitHub Trending；发现/查找/推荐 AI 开源项目；
  询问今日 GitHub 上有什么热门 AI/LLM/Agent 仓库；查看 daily trending AI repos、
  what's hot on GitHub for AI、trending open-source AI projects。
  同时供 collector Agent 及下游分析管线调用。
---

# GitHub Trending 采集

## 执行步骤

### 1. 抓取榜单

访问 `https://github.com/trending?since=daily`，解析页面，逐条提取仓库基本信息（name、url、stars、language、topics、description）。

**完成条件**：成功提取 ≥ 25 条仓库记录，每条记录 6 个字段无空值。
**降级路径**：页面解析失败或条目不足 25 条时，回退到 `https://github.com/trending` 全量榜单重新抓取。

### 2. 过滤

**纳入**：topics 命中 `ai` / `llm` / `agent` 任一关键词即保留。

**丢弃**：
- awesome 列表（名称含 `awesome-` 或 topics 含 `awesome-list`）
- 教程、课程聚合、面试题、个人笔记

**完成条件**：逐条核验过滤结果，最终条目数 5–20 条，无不属于 AI/LLM/Agent 方向的漏网项目。

### 3. 去重

以 `url` 为键去重。

**完成条件**：列表中不再存在重复 `url`。

### 4. 生成摘要

为每条生成中文摘要，公式：**项目名 + 做什么 + 为什么值得关注**，≤ 150 字。拒绝空泛形容词，突出核心技术能力。

**完成条件**：每条摘要均已填充，长度均 ≤ 150 字。

### 5. 排序截取

按 `stars` 降序排列，取前 15 条。

**完成条件**：输出列表长度 ≤ 15。

### 6. 落盘

写入 `knowledge/raw/github-trending-{YYYY-MM-DD}.json`（UTC 日期，ISO 8601）。

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-07-22T10:00:00Z",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "summary": "项目名 + 做什么 + 为什么值得关注",
      "stars": 1234,
      "language": "Python",
      "topics": ["ai", "llm", "agent"]
    }
  ]
}
```

**完成条件**：JSON 文件已创建，UTF-8 编码无非法字符，`collected_at` 为 ISO 8601 UTC 时间。

## 护栏

- 仅通过 WebFetch 读取页面内容，不执行 git clone、pip install 等任何本地代码。
- 当日无 AI 匹配结果时，降级到 `https://github.com/trending` 全量榜单重新过滤；不报错、不静默丢弃。
