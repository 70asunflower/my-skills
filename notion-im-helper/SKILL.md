---
name: notion-im-helper
description: Sync IM messages to Notion via Notion API. Supports 7 content types, 4 formats, 2 metadata types. Append-only to a single Notion page.
---

# Notion IM Helper

通过消息自动同步内容到 Notion。支持日记、笔记、待办、想法、问题、链接、摘抄 7 种类型。

## Environment Variables

- `NOTION_API_KEY` - Notion Integration Token
- `NOTION_PARENT_PAGE_ID` - Target Notion Page ID (32 chars)
- `NOTION_QUOTES_PAGE_ID` (optional) - Separate page for quotes

## Setup

1. `pip install notion-client`
2. Set env vars: `NOTION_API_KEY` and `NOTION_PARENT_PAGE_ID`
3. Authorize integration on Notion page (··· > Connect to)

## Usage

When the user sends a message matching a trigger pattern, execute the corresponding script:

```bash
python scripts/record.py record --type {type} "{content}"
python scripts/record.py heading --level {1|2|3} "{text}"
python scripts/record.py divider
python scripts/record.py list --kind {bullet|number} "{items}"
python scripts/record.py toggle "{json}"
python scripts/record.py image [--caption "text"] "{file_path_or_url}"
python scripts/record.py undo
python scripts/check_config.py
python scripts/summary.py {monthly|quote}
```

## Trigger Rules

**Content types** (prefix → type):
- `日记:` / `今天:` / `riji:` / `d` → diary
- `笔记:` / `学习:` / `note:` / `n` → note
- `待办:` / `todo:` / `t` → todo
- `done:` / `完成:` / `√ ` → done
- `想法:` / `灵感:` / `idea:` / `flash:` / `闪念:` / `i` → idea
- `问题:` / `疑问:` / `q:` → question
- `摘抄:` / `quote:` / `qu:` / `z` → quote
- `链接:` / `link:` / `url:` / `l` → link
- `图片:` / `photo:` / `img:` / `p` → image

**Formats:**
- `* text` → H1 heading
- `** text` → H2 heading
- `*** text` → H3 heading
- `> text` → quote block
- `---` → divider
- `- text` → bulleted list
- `1. text` / `2. text` etc → numbered list
- `toggle: title` + subsequent `-` / `--` / `---` lines → toggle block

**Commands:**
- `月报` / `monthly` → extract current month records for summary
- `摘抄` / `随机摘抄` → random historical entry
- `搜: xxx` / `search: xxx` → search records by keyword
- `撤回` / `undo` → delete last batch of blocks (within 5 min window)
- `配置检查` / `check config` → verify config

**Smart detection** (no prefix, AI infers):
- Pure URL → link
- Starts with YYYY-MM-DD → diary
- Contains `[ ]` or `【 】` → todo
- Default → idea

## Metadata

Scan the LAST line for metadata:
- `#关键词` → tag
- `/p:项目名` → project
- Remove metadata from content before passing to script

## Batch & Undo

- Multi-line messages: each format line (heading/quote/divider/list) becomes a separate block, sent in a single API call
- Undo within 5 minutes: deletes all blocks from the last batch
- Undo after 5 minutes: deletes only the last single block
- Day separator: a divider is auto-inserted when the last record is from a different day

## Output Protocol

Scripts emit standardized output prefixes:
- `OK|message` → success, relay success message to user
- `ERROR|CONFIG` → guide user to set up Notion integration
- `ERROR|AUTH` → invalid API key or page not authorized
- `ERROR|RATE_LIMIT` → tell user to wait
- `ERROR|NETWORK` → tell user to retry later

Always run `check_config.py` first on first use. Never modify or delete existing Notion blocks.

## Image Upload

- Supports **local file paths** (e.g., `C:\Users\photos\img.jpg`) and **HTTP URLs** (e.g., `https://example.com/photo.png`)
- Local files are uploaded to Notion servers via the File Upload API, then attached as image blocks
- URL images are referenced directly as external image blocks
- Optional `--caption` flag to add caption text to the image
- Max file size: 5MB (Notion API limit)
- Supported formats: jpg, jpeg, png, gif, webp, bmp, svg
