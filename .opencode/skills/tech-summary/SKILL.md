---
name: tech-summary
description: 当需要对采集的技术内容进行深度分析总结时使用此技能
allowed-tools: Read, Grep, Glob, WebFetch
---

# 技术深度分析技能

## 使用场景

读取 `knowledge/raw/` 目录下当日采集的原始数据，对每条项目进行深度分析，生成摘要、技术亮点、评分和标签建议，识别跨项目的共同趋势，输出结构化分析结果供下游落盘和推送。

## 执行步骤

### 第 1 步：读取最新采集文件

- 使用 `Glob` 列出 `knowledge/raw/` 下所有 JSON 文件
- 选取当日（UTC）最新的采集文件
- 解析 JSON，提取 `items` 数组，确认条目数量 ≤ 15

### 第 2 步：逐条深度分析

对每条项目产出以下分析维度：

**摘要**（≤ 50 字）
- 拒绝罗列功能堆砌，一句话讲清核心价值
- 示例："将 AI Agent 嵌入浏览器自动化，用自然语言驱动 Playwright，替代手写测试脚本。"

**技术亮点**（2–3 条，用事实说话）
- 每条 30 字以内，必须有具体数据或技术特征支撑
- 示例："v3.0 引入流式图执行引擎，benchmark 吞吐提升 3 倍"
- 禁止空泛描述（如 "性能很好"、"功能强大"）

**评分**（1–10 分，附理由）

| 分数 | 含义 |
|------|------|
| 9–10 | 改变格局，赛道标杆或范式级创新 |
| 7–8 | 直接有帮助，解决实际痛点、可落地 |
| 5–6 | 值得了解，场景有潜力但尚未验证 |
| 1–4 | 可略过，早期 Demo 或已有更优替代 |

**约束：15 个项目中 9–10 分不超过 2 个。**

**标签建议**（≥ 3 个英文标签）
- 技术栈：`python` `typescript` `rust` `go`
- 领域：`llm` `agent` `rag` `vision` `fine-tuning`
- 范式：`workflow` `multi-agent` `tool-calling` `low-code`
- 部署：`self-hosted` `cloud` `cli` `web`

### 第 3 步：趋势发现

基于全量分析结果，提炼：

- **共同主题**：多个项目共同关注的方向（如 "本周 5 个项目聚焦 Agent 可观测性"）
- **新概念**：出现的新范式或术语（如 "MCP 协议成为工具调用标配"）

趋势发现写在 `trends` 字段中，2–4 条即可，每条 ≤ 40 字。

### 第 4 步：输出分析结果 JSON

将分析结果写入 `knowledge/raw/tech-summary-YYYY-MM-DD.json`（日期为 UTC 当日）。

## 输出格式

```json
{
  "source": "tech-summary",
  "skill": "tech-summary",
  "analyzed_at": "2026-07-21T12:00:00Z",
  "total": 10,
  "trends": [
    "Agent 可观测性成为本周热点，5 个项目提供 tracing/eval 方案",
    "MCP 协议被多个项目作为默认工具集成方式"
  ],
  "items": [
    {
      "name": "langgenius/dify",
      "url": "https://github.com/langgenius/dify",
      "summary": "开源 LLM 应用开发平台，可视化编排 RAG 与 Agent 工作流，14 万 Star。",
      "highlights": [
        "可视化拖拽编排，降低 Agent 开发门槛至非技术人员",
        "内置 RAG 引擎支持 100+ 模型，社区生态活跃"
      ],
      "score": 8,
      "score_reason": "LLM 应用平台赛道领先者，开箱即用的 RAG + Agent 能力直接帮助中小团队落地",
      "tags": ["llm", "agent", "rag", "workflow", "self-hosted"]
    }
  ]
}
```

## 评分约束

- 单次分析 9–10 分条目 **不超过 2 个**
- 若超过 2 个，降序保留 top 2，其余强制降为 8 分
- 5–6 分段至少占总量 30%
- 评分要有区分度，不得大面积打 8 分

## 注意事项

- 所有日期和时间使用 UTC 时区
- `analyzed_at` 为 ISO 8601 格式
- 输出 JSON 编码为 UTF-8，禁止非 UTF-8 非法字符
- 摘要 ≤ 50 字须逐条核验
- 技术亮点必须含具体数据或技术特征，禁止空泛形容词
- 不执行任何代码
- 所有操作带可追溯的 `trace_id`
