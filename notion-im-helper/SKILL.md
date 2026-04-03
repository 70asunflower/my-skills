---
name: notion-im-helper
description: "当用户需要记录想法到 Notion 时触发此 Skill。支持通过 IM/消息的方式向 Notion 追加内容：日记、笔记、待办、想法、问题、链接、摘抄等。支持 7 种内容类型 + 4 种格式 + 2 种元数据。当消息包含关键字触发（日记/今天/笔记/学习/待办/todo/想法/灵感/问题/摘抄/链接/日报/周报/撤回）或使用前缀快捷键（d/n/t/i/q/z/l）时触发。只追加不修改，单页时间线设计，安全可靠。"
---

# Notion IM Helper

通过消息自动同步内容到 Notion Page。核心价值：**发消息就记好了**。

## Setup

首次使用需要配置：

1. 获取 Notion Integration Token: https://www.notion.so/my-integrations
2. 获取目标 Notion 页面 ID（URL 中 32 位字符）
3. 设置环境变量：
```bash
# Windows PowerShell
$env:NOTION_API_KEY="ntn_xxx"
$env:NOTION_PARENT_PAGE_ID="32位id"
```
4. 授权 Integration 到页面：页面右上角 ··· → Connect to → 选择 Integration

## Trigger Rules

当用户发送以下格式消息时，解析并执行对应记录操作：

### Content Types (7 types + 1 derived)

| 前缀 | 快捷方式 | 说明 |
|------|---------|------|
| `日记:` / `今天:` / `riji:` | → diary |
| `笔记:` / `学习:` / `note:` | → note |
| `待办:` / `todo:` | → todo |
| `想法:` / `灵感:` / `idea:` | → idea |
| `问题:` / `疑问:` / `q:` | → question |
| `摘抄:` / `quote:` / `qu:` | → quote |
| `链接:` / `link:` / `url:` | → link |
| `done:` / `完成:` / `√` | → done (todo checked) |

### Shortcut Keys (single letter prefix)
- `d ` at start → diary
- `n ` at start → note
- `t ` at start → todo
- `i ` at start → idea
- `q ` at start → question
- `z ` at start → quote
- `l ` at start → link

### Format Types
- `* text` → heading H1
- `** text` → heading H2
- `*** text` → heading H3
- `> text` → quote block
- `---` → divider
- `- text` → bulleted list
- `1. text` → numbered list
- `toggle: title` + child lines (`-` / `--` / `---`) → toggle block

### Commands
- `日报` / `daily` / `今日` / `today` → show today's records
- `周报` / `weekly` → weekly summary
- `摘抄` / `随机摘抄` → random historical entry
- `撤回` / `undo` → delete last block
- `配置检查` / `check config` → verify config

### Smart Detection (no prefix → AI infers)
- Pure URL → link
- Starts with YYYY-MM-DD → diary
- Contains `[ ]` → todo
- Otherwise → idea

### Metadata
- `#关键词` → tag (at message end)
- `/p:项目名` → project (at message end, before tags)

### Multi-Line Messages
Parse each line independently. Group sequential same-type lines.
- `notion` alone → check config
- `---` → divider
- Format line → block immediately after

## Implementation

Use these scripts located in `notion-im-helper/scripts/`:

```bash
# Content recording
python scripts/record.py record --type {type} "{content}"
python scripts/record.py heading --level {1|2|3} "{text}"
python scripts/record.py divider
python scripts/record.py list --kind {bullet|number} "{items}"
python scripts/record.py toggle '{"title":"xx","children":[...]}'
python scripts/record.py undo
python scripts/check_config.py
python scripts/daily_summary.py {daily|weekly|quote}
```

## Output Protocol

Scripts emit standardized prefixes. Relay the message after `|`:
- `OK|xxx` → relay success (e.g., "已记录到 Notion ✅")
- `ERROR|CONFIG` → guide user to set up config
- `ERROR|AUTH` → "API Key 无效或页面未授权"
- `ERROR|RATE_LIMIT` → "记录太快了，稍等再发~"
- `ERROR|NETWORK` → "网络不太通畅，稍后再试~"

## Safety Rules

- **ALWAYS** run `check_config.py` first on first use
- **NEVER** modify/delete existing blocks (except `undo`)
- **NEVER** expose API keys or error stacks
- **ALWAYS** return friendly messages
- All Notion access via scripts, never direct API manipulation
