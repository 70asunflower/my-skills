---
name: notion-im-helper
description: "通过消息自动同步内容到 Notion Page。支持日记、笔记、待办、想法、问题、链接、摘抄等 7 种内容类型 + 多级标题/列表/折叠等排版格式。只追加不修改，单页时间线设计，安全可靠。"
metadata:
  openclaw:
    emoji: 📝
    requires:
      bins:
        - python3
      env:
        - NOTION_API_KEY
        - NOTION_PARENT_PAGE_ID
      optional:
        - NOTION_QUOTES_PAGE_ID
    install:
      - id: python-deps
        kind: note
        label: "需要安装依赖：pip install notion-client httpx[socks]"
    primaryEnv: NOTION_API_KEY
---

# Notion IM Helper

通过即时通讯软件发送消息，自动追加到 Notion Page。底层脚本处理按天聚合和多彩类型 Emoji 与时间戳，AI **只需解析意图并调用对应脚本**。

> **[核心原则 — 每次执行前必须重读此区块]**
> 🚫 **NEVER DELETE/MODIFY**: 只能追加（Append），严禁修改/删除已有块。
> 🚫 **NEVER EXPOSE ERRORS**: 错误时使用友好话术，不要暴露技术堆栈。
> ✅ **MUST USE SCRIPTS**: 必须使用 `scripts/` 下的 Python 脚本，**不要自己实现 Notion API 请求**。

---

## 🧩 语义级智能匹配与调用表（意图 > 格式）

> ⚠️ **绝对最高优先级匹配原则：意图 > 格式**
> 只要用户输入**在语义上**符合下面的功能，请**大胆认定其意图！**. 无论冒号是中文还是英文、用空格还是逗号紧跟文字、用中文还是英文，都要识别。绝不准向用户挑错格式问题。提取核心正文，将 `#标签` 和 `【项目】` 通过参数传入相应脚本。

### 内容录入类

| 用户语义/特征 | 随意输入示例 | 对应脚本调用 |
|--------------|-------------|------------|
| **(默认) 日常/日记** | `今天被老板骂了QAQ` | `python3 {SCRIPTS}/add_record.py "正文" --type diary` |
| **学习/体系化笔记** | `笔记：Python内存分代...` / `学习-Git原理` | `python3 {SCRIPTS}/add_record.py "正文" --type note` |
| **闪念/突发奇想** | `flash，刚想到个好点子` / `闪念: 买一把新伞` | `python3 {SCRIPTS}/add_record.py "正文" --type flash` |
| **产品灵感/想法** | `idea 可以做个记账工具` | `python3 {SCRIPTS}/add_record.py "正文" --type idea` |
| **提问/遇到问题** | `疑问：为什么前端又跨域了` | `python3 {SCRIPTS}/add_record.py "正文" --type question` |
| **复盘/周月总结** | `本周学习小结：...` | `python3 {SCRIPTS}/add_record.py "正文" --type summary` |
| **日常待办/购物清单** | `待办事项 洗车、买菜` / `todo：交电费` | `python3 {SCRIPTS}/add_todo.py "任务1" "任务2"` |
| **已搞定的任务** | `√ 报销 发票` / `✓做完PPT了` | `python3 {SCRIPTS}/add_todo.py "纯任务名" --done` |
| **保存网页链接** | `帮我存一下这个网址 https://...` | `python3 {SCRIPTS}/add_link.py "网址URL"` |
| **名言/引用摘抄** | `摘抄：人生如逆旅...` / `> 一万年太久` | `python3 {SCRIPTS}/add_quote.py "纯引用文字"` |
| **搜寻过往卡片** | `帮我搜一下缓存相关的笔记` | `python3 {SCRIPTS}/search_notes.py "关键字"` |

### 排版类指令

| 结构特征 | 示例 | 对应脚本调用 |
|---------|------|------------|
| 一/二/三级标题 | `*周报` / `***小结` | `python3 {SCRIPTS}/add_heading.py <级别1-3> "标题"` |
| 无序列表项 | `- 买苹果` | `python3 {SCRIPTS}/add_list.py bullet "文本"` |
| 有序列表项 | `1. 第一步` | `python3 {SCRIPTS}/add_list.py number "文本"` |
| 下拉折叠列表 | `下拉：我的计划` | （通过管道传规范化 JSON 至 `{SCRIPTS}/add_toggle.py`） |
| 分割线 | `---` | 在下一条记录调用时脚本自动处理 |

### 查询类指令

| 指令 | 对应脚本调用 |
|------|------------|
| `日报` / `daily` / `今日` | `python3 {SCRIPTS}/daily_summary.py daily` |
| `周报` / `weekly` | `python3 {SCRIPTS}/daily_summary.py weekly` |
| `随机摘抄` / `摘抄` | `python3 {SCRIPTS}/daily_summary.py quote` |

### 标签与项目提取

输入：`待办: 预定机票 #生活 【旅行】`

处理流程：
1. **提取正文**: "预定机票"
2. **提取参数**: `--tag 生活` `--project 旅行`
3. **最终命令**: `python3 {SCRIPTS}/add_todo.py "预定机票" --tag 生活 --project 旅行`

### 智能盲猜与多行解析

1. **无触发前缀的随意短句**: 发挥语义理解能力盲猜！全是琐碎感慨就是 `--type diary`，长篇知识就是 `--type note`。
2. **多行混合文本**: 拆开按顺序多次独立调用不同脚本！一切在底层安静完成，最后给整合回复。

---

## Output Protocol

Scripts emit standardized prefixes. Relay the message after `|`:
- `OK|xxx` → relay as "已记录到 Notion ✅"（可简单概括类型）
- `ERROR|CONFIG` → guide user to set up `NOTION_API_KEY` and `NOTION_PARENT_PAGE_ID`
- `ERROR|AUTH` → "API Key 无效或页面未授权"
- `ERROR|RATE_LIMIT` → "记录太快了，稍等再发~"
- `ERROR|NETWORK` → "网络不太通畅，稍后再试~"

---

## Safety Rules

- **ALWAYS** 首次执行前用 `scripts/notion_helper.py` 的 `check_config()` 验证配置
- **NEVER** 修改/删除已有块（仅 undo 例外）
- **NEVER** 暴露 API Key 或错误堆栈
- **ALWAYS** 返回友好提示语术
- 所有 Notion 操作通过脚本完成，禁止直接调 API
