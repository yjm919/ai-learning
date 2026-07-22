# 10 — 飞书推送 + 幂等回填

**Blocked by:** 08

**Status:** ready-for-agent

## What to build

飞书 Webhook 推送 Markdown 日报。`published_at` 已设 → 跳过；未设 → 推送成功回填。失败标注异常不静默。

## Acceptance Criteria

- [ ] `.opencode/skills/feishu-push.md` — Organizer 推送技能
- [ ] `src/pushers/feishu.py` — Webhook 富文本消息发送
- [ ] `FEISHU_WEBHOOK_URL` 从环境变量注入
- [ ] 推送前检查 `published_at`：已设跳过
- [ ] 推送成功后回填 `published_at` 到 JSON 文件
- [ ] 失败记录 ERROR + 标注异常
- [ ] 崩溃重跑不重复推送（幂等）
- [ ] 单元测试：幂等跳过、成功回填、失败异常
