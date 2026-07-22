# 09 — Telegram 推送 + 幂等回填

**What to build:** 将 Markdown 日报推送到 Telegram 频道。通过 `published_at` 字段实现幂等：已推送的条目跳过，未推送的推送成功后才回填 `published_at`。推送失败标注当日异常，不静默丢弃。

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] `.opencode/skills/telegram-push.md` 存在
- [ ] `src/pushers/telegram.py` 实现 Telegram Bot Markdown 消息发送
- [ ] Bot Token 和 Chat ID 通过环境变量注入（`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`）
- [ ] 推送前检查 `published_at`：已设置则跳过
- [ ] 推送成功后回填 `published_at` 到文章 JSON 文件
- [ ] 推送失败记录 ERROR 日志，标注当日异常
- [ ] 崩溃重跑不重复推送（幂等）
- [ ] 所有操作带 `trace_id` 日志
- [ ] 单元测试覆盖：幂等跳过、成功回填、失败异常标注
