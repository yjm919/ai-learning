# 02 — Article JSON Schema + 校验 + 重试

**Blocked by:** None

**Status:** ready-for-agent

## What to build

知识条目 JSON Schema 定义与校验函数。Analyzer 产出条目后自动 schema 校验（必填字段、类型、UTF-8、ISO 8601），不合规最多重试 3 次，全部失败落 `status=error`。

## Acceptance Criteria

- [ ] `src/schemas/article.schema.json` — 完整 JSON Schema（含 id/title/source/source_url/summary/tags/status/score/fetched_at/analyzed_at/published_at 及约束）
- [ ] `src/validation.py` — `validate_article(data: dict) -> list[str]`，空列表 = 通过
- [ ] `src/validation.py` — `validate_with_retry(generate_fn, max_retries=3) -> dict`，重试 3 次仍失败返回 `status=error` 条目
- [ ] UTF-8 编码校验：非法字符被拒绝
- [ ] ISO 8601 时间格式校验：`fetched_at`、`analyzed_at`、`published_at` 格式正确
- [ ] 单元测试：合法条目通过、缺必填字段拒绝、非法时间拒绝、3 次全失败落 error 兜底
