---
name: notion-im-helper
description: Sync IM messages to Notion via Notion API. Supports 7 content types, 4 formats, 2 metadata types, multi-page sync. Append-only.
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

## Directory Structure

```
scripts/
├── core/                  # Generic, portable — no user data
│   ├── blocks.py          # Block builders (callout, paragraph, image, etc.)
│   ├── dispatch.py        # Content dispatch & format parsing
│   └── __init__.py
├── user/                  # Personalized — your config only
│   ├── pages.json         # Named page ID mappings (e.g., "lifeos")
│   └── README.md
├── record.py              # Entry point (imports from core/)
├── notion_client.py       # Notion API client
├── check_config.py        # Config verification
├── search_notes.py        # Keyword search
└── summary.py             # Monthly summaries
```

## Multi-Page Support

You can sync to multiple Notion pages by configuring named pages in `scripts/pages.json`:

```json
{
  "lifeos": {
    "page_id": "372294df130c81d4b3cae4dd797d924b",
    "description": "8+1 Life OS"
  },
  "work": {
    "page_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "description": "工作日志"
  }
}
```

Then use `--page <name>` in any command:
```bash
python scripts/record.py record --type diary --page lifeos
python scripts/record.py image --page lifeos "image.jpg"
python scripts/record.py undo --page lifeos
```

Without `--page`, defaults to `NOTION_PARENT_PAGE_ID`.

**For AI callers**: If user says "notion lifeos 日记:" or mentions "lifeos" page, add `--page lifeos`. Otherwise omit `--page` for the default page.

## Usage

When the user sends a message matching a trigger pattern, execute the corresponding script:

```bash
python scripts/record.py record --type {type} "{content}"
python scripts/record.py record --type {type} --page {name} "{content}"
python scripts/record.py record --type {type} --file {file_path}
python scripts/record.py heading --level {1|2|3} "{text}"
python scripts/record.py divider
python scripts/record.py list --kind {bullet|number} "{items}"
python scripts/record.py toggle "{json}"
python scripts/record.py image [--caption "text"] "{file_path_or_url}"
python scripts/record.py image --page {name} [--caption "text"] "{file_path_or_url}"
python scripts/record.py caption "{content_to_append}"
python scripts/record.py undo
python scripts/check_config.py
python scripts/search_notes.py "{keyword}"
python scripts/summary.py {monthly|quote}
```

## Trigger Rules

> **⚠️ FIRST CHECK — OS vs Page routing (MUST check before anything else)**

The two pipelines are **mutually exclusive**. Never let a message fall through from one to the other.

```
Message arrives
    ↓
STEP 0: Starts with "os " (case-insensitive)?
    → YES: Route to OS Sync (§ below). STOP. Do NOT check page triggers.
    → NO:  Route to Page Sync (§ below).
```

**OS Sync** (OS Sync — 8+1 Life OS section) → structured database rows.
**Page Sync** (rest of this section) → append callout blocks to page.

### Page Sync Triggers (only if NOT "os ")
- `日记:` / `今天:` / `riji:` / `d` → diary
- `笔记:` / `学习:` / `note:` / `n` → note
- `待办:` / `todo:` / `t` → todo
- `done:` / `完成:` / `√ ` → done
- `想法:` / `灵感:` / `idea:` / `flash:` / `闪念:` / `i` → idea
- `问题:` / `疑问:` / `q:` → question
- `摘抄:` / `quote:` / `qu:` / `z` → quote
- `链接:` / `link:` / `url:` / `l` → link
- `图片:` / `photo:` / `img:` / `p` → image
- `caption:` / `说明:` / `补:` → caption (append to last entry)

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

**Caption — two distinct uses:**

`caption:` / `说明:` / `补:` has **two different behaviors** depending on context:

### 1. Caption Append (standalone — no image/link in message)

When the user sends `caption:` as the **primary prefix** of a message with **no images or links**, it appends gray-colored paragraphs inside the last callout block:

- `caption: 补充一个角度` → appends "补充一个角度" as a gray paragraph inside the last callout
- `说明: 这个想法还有一个延伸` → same behavior
- `补: 对了还有一点` → same behavior

**Implementation**: Write content to `.pending_content.txt`, then run `python scripts/record.py caption`.

**Visual**: Gray-colored paragraphs inside the callout, visually distinct from the main content. No `↳` prefix.

### 2. Caption Separator (with image/link in message)

When the message **contains images or links**, `caption:` acts as a **separator** between diary content and image/link caption:
- `OPPO园区很好 caption: 园区环境` + 3 images → last image gets caption "园区环境", diary "OPPO园区很好" synced separately
- Without `caption:`, all text is diary/idea content, no caption on images

**IMPORTANT**: The AI must check whether the message contains images or links to determine which caption behavior to use.

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

## Image + Text Sync Rules

When user sends **both image and text** in one message:

1. Parse text: split by `caption:` / `说明:` keyword (if present) — this is the **Caption Separator** mode
   - **Before `caption:`** → diary/idea/note content (synced as callout)
   - **After `caption:`** → image caption (added to last image via `--caption`)
2. Upload images: first N-1 images without caption, **last image with `--caption`**
3. Sync text: write diary/idea content to `.pending_content.txt`, then `record.py record --type {type}`

**Examples**:
- `OPPO园区很好 caption: 园区环境` + 3 images → last image gets caption "园区环境", diary "OPPO园区很好" synced separately
- `这张图有意思` + 1 image → no caption keyword, so no caption on image, "这张图有意思" synced as idea
- 2 images only → just upload both, no caption, no callout

**IMPORTANT**:
- Image and text are always **separate operations** — image via `record.py image`, text via `record.py record`
- Do NOT put image and text in the same command
- When user sends **image only** (no text or just "同步到notion"), upload the image as-is using `record.py image`. Do NOT transcribe/OCR the image content into a callout
- **CRITICAL — No double sync**: When message starts with `caption:` and has an image, the text after `caption:` goes ONLY as image caption (via `--caption`). Do NOT also create a diary/note callout with the same text. If `caption:` is the FIRST keyword (no text before it), the entire content is caption-only — zero callout blocks.

## Link + Caption

Same `caption:` pattern works for links:
- `链接: https://example.com caption: 好文章` → bookmark with caption "好文章"
- Without `caption:`, just a plain bookmark card (Notion auto-fetches title)

**Implementation for link + caption**: Write **URL + caption text together** to `.pending_content.txt`, then run `record.py record --type link`. The code auto-extracts URLs and uses remaining text as bookmark caption. Do NOT sync link and caption separately — `cmd_caption` only appends to callout blocks, not bookmark blocks.

## Long Content Auto-Split

- **≤2000 chars**: Single callout (most entries)
- **>2000 chars**: Auto-split into multiple callouts at paragraph boundaries (e.g., 3-4k chars → 2-3 callouts)
- Metadata (tags/projects) only added to the last callout
- AI should write the **entire content** to `.pending_content.txt` at once — do NOT manually split into multiple calls

## Best Practices for AI Callers

- **Content passing**: Always use `.pending_content.txt` (write file → run script). Never pass content via command-line args (PowerShell `$` expansion issues).
  - **⚠️ CRITICAL — File path**: Write to `C:\Users\Nesp\.workbuddy\skills\notion-im-helper\scripts\.pending_content.txt` (the scripts directory, NOT the workspace directory). The script reads from its own directory, so writing to the workspace root will result in empty content.
- **Image passing**: Pass image file path or URL directly as command-line argument to `record.py image`. Do NOT copy to `.pending_image.jpg` — that file is only used internally for cleanup.
- **Type inference**: If user says "notion" or "同步" without specifying type, infer from content:
  - Starts with `caption:` / `说明:` / `补:` → caption (append to last entry)
  - Contains "日记"/"今天" → diary
  - Contains URL → link
  - Image only → image (use `record.py image`)
  - Default → idea
- **Undo**: Use `record.py undo` — respects 5-min batch window, deletes all blocks from last batch.

## OS Sync — 8+1 Life OS

以 `os` 命名空间前缀触发，同步到结构化数据库。**与页面同步互斥，绝不串线。**

### Trigger Detection

消息以 `os `（不区分大小写）开头时，**立即**进入 OS 同步流程。不检查页面触发词。

> ❌ 错误: `i 想法` → OS sync（没 `os` 前缀，走页面）
> ✅ 正确: `os i 想法 @学习` → OS sync
> ✅ 正确: `i 想法` → page sync（idea callout）
> ❌ 错误: `os 月报` → 错误路由到页面 monthly summary（已修复）

**AI 调用的第一条规则**：先检查 `os ` 前缀。命中则 OS sync，没命中才往下看页面触发词。

### OS Commands

```bash
python scripts/os_entry.py "os l 晨跑5公里 @身体 energy:h duration:30"
python scripts/os_entry.py "os i 试试Obsidian做知识图谱 @学习 source:ai"
python scripts/os_entry.py "os h 冥想"
python scripts/os_entry.py "os 今天"
```

### Command Routing

| 触发 | 命令 | 目标数据库 | 说明 |
|------|------|-----------|------|
| `os l` / `os log` / `os 记录` | 活动记录 | Daily Log | 记录做了什么，可带属性 |
| `os i` / `os idea` / `os 灵感` | 灵感捕捉 | Idea Inbox | 快速捕捉想法 |
| `os h` / `os habit` / `os 打卡` | 习惯打卡 | Habit Log | 标记习惯完成 |
| `os hs` / `os streaks` | 查看 streak | Habits | 更新并显示连续天数 |
| `os 今天` | 今日摘要 | Daily Log | 查看今日活动 |
| `os 本周` | 本周汇总 | Daily Log | 近 7 天活动 |
| `os 桶 @身体` | 桶查询 | Daily Log | 某桶近 14 天记录 |
| `os 灵感列表` | 灵感列表 | Idea Inbox | 查看未处理灵感 |
| `os 周报` / `os wr` | 周回顾 | Weekly Review | Agent 生成周报 |
| `os 月报` / `os mr` | 月复盘 | Periodic Review | Agent 生成月报 |

### Attribute Syntax

用空格分隔的属性语法，AI 通过 `os_parser.py` 自动解析：

| 属性 | 语法 | 示例 |
|------|------|------|
| 桶 | `@桶名` | `@身体` `@Learning` `@Body` |
| 能量 | `energy:h/m/l` | `energy:h` (高/中/低) |
| 心情 | `mood:great/good/neutral/low/terrible` | `mood:good` |
| 时长 | `duration:N` | `duration:30` (分钟) |
| 来源 | `source:xxx` | `source:ai` `source:book` |
| 紧急度 | `urgency:now/thisweek/later` | `urgency:now` |
| 备注 | `note:xxx` `备注:xxx` | `note:天气不错` |

**桶名匹配**：支持中英文（`@身体` = `@Body`），不区分大小写。未知桶名会返回可用列表。

### Content vs Notes — 分开存

- **Content（标题）**：一句话「做了什么」，如「写作 320 字」「晨跑 5 公里」。这是列表里显示的那行。
- **Notes（备注）**：补充细节、感受、对不上选项的原话放这里。如「状态不错，挺有成就感」。

AI 调用时，若消息含描述性文字（超过动作本身），把动作放 Content，其余放 Notes：
```
os l 写作320字，状态不错挺有成就感 @学习 energy:h
→ Content: "写作320字"
→ Notes: "状态不错，挺有成就感"
```

### Smart Inference（无显式属性时自动推断）

**Energy 口语映射**：
- 累 / 没劲 / 困 → `energy:l`
- 一般 / 还行 / 正常 → `energy:m`
- 精神好 / 精力充沛 / 有干劲 → `energy:h`

**Mood 口语映射**：
- 开心 / 有成就感 / 爽 → `mood:good` 或 `mood:great`
- 一般 / 还行 → `mood:neutral`
- 烦 / 难受 / 焦虑 / 低能量 → `mood:low` 或 `mood:terrible`

**Bucket 关键词推断**：
- 跑步 / 健身 / 运动 / 饮食 / 睡眠 → @身体
- 读书 / 上课 / 论文 / 学习 / 课程 → @学习
- 工作 / 项目 / 写代码 / 开会 / 赚钱 → @赚钱
- 家人 / 父母 / 视频通话 → @家庭
- 朋友 / 聚会 / 社交 → @社交
- 冥想 / 日记 / 独处 / 正念 → @精神
- 开源 / 帮助 / 指导 / 公益 → @服务
- 游戏 / 旅行 / 玩 / 放松 → @玩乐

匹配不到就留空，不回传 bucket 属性。绝不替用户建新桶。

### 多事件拆分

一条消息含多件事时，拆成多条 `os l` 命令分别调用：

```
os l 晨跑5公里 @身体 energy:h duration:30
os l 写代码3小时 @赚钱 energy:m duration:180
os l 晚上和爸妈视频 @家庭
```

### 大小写规则（Notion API 敏感）

所有属性名和 select 值必须精确大小写：
- `Energy`: High / Medium / Low（不是 high）
- `Mood`: Great / Good / Neutral / Low / Terrible（不是 good）
- Daily Log 属性名: `Content, Date, Energy, Duration_min, Bucket, Adventure, Mood, Notes`
- 公式/rollup 字段（`OverallScore`, `TotalCompletions`, `Avg_*`）绝不要写
- `Place` 字段跳过，不要写

### 短记录 vs 长日记（路由）

- `os l` 或无前缀且短 → 建 Daily Log 行（结构化属性）
- `日记:` 或明显长篇/情绪流 → 走原有页面同步（append callout blocks）

### AI 调用流程

1. 检测用户消息以 `os ` 开头
2. **智能推断**（消息无显式属性时）：
   - 扫描关键词推断 bucket（跑步 → @身体）
   - 扫描情绪词推断 energy/mood（累 → energy:l；开心 → mood:good）
   - 提取时长（一小时 → duration:60）
3. **拆解 Content vs Notes**：
   - 把「动作」放 Content（「晨跑5公里」）
   - 把「感受/细节」放 Notes（「状态不错，呼吸顺畅」）
4. 构建完整 os 命令（带推断出的属性），调用 `python scripts/os_entry.py "完整消息"`
5. 解析输出：`OK|...` / `INFO|...` / `ERROR|...`
6. **不需要** `.pending_content.txt` 文件（OS 直接传参）

### OS vs Page Sync — 严格互斥（MUST）

两个管道**绝不串线**。`os ` 开头 → OS 同步，否则 → 页面同步。没有歧义、没有回退、没有"两者都试试"。

| 消息 | 正确管道 | 错误管道 |
|------|---------|---------|
| `os l 晨跑 @身体` | OS → Daily Log 行 | — |
| `os i 灵感 @学习` | OS → Idea Inbox 行 | — |
| `i 随便一个想法` | Page → idea callout | ❌ 别走 OS |
| `想法: 好主意` | Page → idea callout | ❌ 别走 OS（没 `os` 前缀） |
| `日记: 今天好累` | Page → diary callout | ❌ 别走 OS |
| `月报` | Page → monthly summary | ❌ 别走 OS（`os 月报` 才对） |
| `os 月报` | OS → 数据库聚合 | ✅ |
