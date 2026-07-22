# 02 — Article JSON Schema + 校验 + 3 次重试

**What to build:** 知识条目的 JSON Schema 定义和校验逻辑。每当 Analyzer 生成一个条目，系统自动校验其 JSON schema（必填字段、类型、UTF-8 编码、ISO 8601 时间格式）。校验失败时重试最多 3 次，全部失败则落 `status=error` 的坏数据，不阻塞管线。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `src/schemas/article.schema.json` 定义完整 JSON Schema（含 id、title、source、source_url、summary、tags、status、score、fetched_at、analyzed_at、published_at、metrics 等字段及约束）
- [ ] `src/validation.py` 实现 `validate_article(data: dict) -> list[str]` 返回错误列表，空列表 = 通过
- [ ] `src/validation.py` 实现 `validate_with_retry(generate_fn, max_retries=3) -> dict` — 调用 LLM 生成 → 校验 → 最多重试 3 次 → 全部失败返回 `status=error` 的条目
- [ ] UTF-8 编码校验
- [ ] ISO 8601 时间格式校验
- [ ] 单元测试覆盖：合法条目通过、缺少必填字段拒绝、非法时间格式拒绝、3 次全部失败落 error 条目
