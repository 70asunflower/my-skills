# Feishu Bot 配置检查清单

## 配置前准备

- [ ] 已创建飞书应用并获取 App ID 和 App Secret
- [ ] 已在飞书开放平台启用机器人能力
- [ ] 已设置好事件订阅（Webhook）指向 OpenClaw Gateway
- [ ] 已发布应用到企业或组织

## 配置步骤

### 1. 创建 .env 文件
- [ ] 在 `~/.openclaw/workspace-<agent_name>/` 目录创建 `.env` 文件
- [ ] 包含 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`

### 2. 配置 openclaw.json
- [ ] 在 `channels.feishu.accounts` 中添加账号配置
- [ ] 在 `bindings` 中添加路由绑定

### 3. 重启 Gateway
- [ ] 执行 `openclaw gateway restart`

### 4. 用户配对
- [ ] 用户在飞书中与 Bot 对话，获取配对码
- [ ] 管理员执行 `openclaw pairing approve feishu <CODE>`

## 故障排查

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| Bot 无反应 | 缺少 channels.feishu.accounts 配置 | 检查 openclaw.json |
| Bot 无反应 | 缺少 bindings 路由 | 检查 bindings 配置 |
| Bot 无反应 | Gateway 未重启 | 执行 gateway restart |
| 提示未配对 | 用户未执行配对批准 | 执行 pairing approve |
| 提示凭证错误 | App Secret 错误 | 检查 .env 文件 |
