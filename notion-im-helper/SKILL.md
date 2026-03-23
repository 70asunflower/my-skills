---
name: notion-im-helper
description: "通过即时通讯(IM)向 Notion 添加内容。支持日记、待办清单、多级标题、引用、网页书签等。当用户发送消息时，智能解析类型并打花标签和Emoji存入 Notion 中。只追加不删除，安全可靠。"
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

通过即时通讯软件发送消息，自动同步到 Notion 页面。底层脚本会自动处理按天聚合（跨天自动加分割线）和多姿多彩的类型 Emoji 与时间戳抬头，AI **只需负责解析意图并调用对应的 Python 脚本**。

> **[核心原则 — 每次执行前必须重读此区块]**
> 🚫 **NEVER DELETE/MODIFY**: 只能追加（Append），严禁修改/删除已有块。
> 🚫 **NEVER EXPOSE ERRORS**: 错误时使用友好话术，不要暴露技术堆栈。
> ✅ **MUST USE SCRIPTS**: 必须使用 `scripts/` 下的 Python 脚本，**不要自己实现 Notion API 请求**。

---

## 🧩 触发规则与脚本调用表

根据用户的输入特征，选择最合适的脚本和参数。**无论用户输入是否含前缀，都需要提取出纯净的正文**，并将提取出的 `#标签` 和 `【项目】` 通过参数传入。
(注：绝不要往脚本传 `--claw` 或 `--source`，该功能已完全下线丢弃)

| 前缀/关键词特征 | 示例 | 触发的功能 | 对应脚本调用格式 |
|-------------|------|-----------|--------------|
| `日记:` / `今天:` / 无前缀 | `今天天气好` | 日记（**默认模式**）| `python3 add_record.py "内容" --type diary` |
| `笔记:` / `学习:` | `笔记: Python装饰器` | 学习笔记 | `python3 add_record.py "内容" --type note` |
| `闪念:` / `flash:` | `突然想到个点子` | 闪念/想法 | `python3 add_record.py "内容" --type flash` |
| `想法:` / `灵感:` | `灵感: 做个工具` | 灵感记录 | `python3 add_record.py "内容" --type idea` |
| `问题:` / `疑问:` | `疑问: 为什么报错` | 记录问题 | `python3 add_record.py "内容" --type question` |
| `总结:` / `回顾:` | `这周学了...` | 周/月总结 | `python3 add_record.py "内容" --type summary` |
| `待办:` / `todo:` / `t` | `todo: 买牛奶` | 待办清单 | `python3 add_todo.py "内容"` |
| `任务:` / `task:` | `task: 写周报` | 任务 | `python3 add_todo.py "内容" --type task` |
| `√` / `✓` / `done:` | `√ 写周报` | 已完成的待办 | `python3 add_todo.py "内容" --done` |
| `链接:` / `link:` / 纯URL | `https://...` | 网页书签 | `python3 add_link.py "网址URL"` |
| `摘抄:` / `quote:` / `>` | `> 这句话真好` | 引用块 | `python3 add_quote.py "引用文本"` |
| `*` / `**` / `***` | `*周报` | 多级标题 | `python3 add_heading.py <级别1-3> "标题"` |
| `- ` (短横+空格) | `- 苹果` | 无序列表 | `python3 add_list.py bullet "文本"` |
| `1. ` / `2. ` 等 | `1. 第一步` | 有序列表 | `python3 add_list.py number "文本"` |
| `下拉:` / `toggle:` | `下拉: 计划` | 下拉列表 | （通过管道传 JSON 至 `add_toggle.py`） |
| `搜:` / `search:` | `搜: API` | 搜索笔记 | `python3 search_notes.py "关键字"` |

### 🤖 智能多行解析与默认模式（极其重要）
如果你收到一段话，**没有任何明显的前缀**（例如直接发了一句“今天发生了一件开心的事” 或 “Python的GIL是什么”），请发挥语义理解能力盲猜：
- 是日常流水账？ -> `--type diary`
- 是突发奇想？ -> `--type idea`
- 是一段知识点？ -> `--type note`
- 是发了一个极简链接？ -> 调用 `add_link.py`

**多行文本**：有些消息可能是混合的（第一行是灵感，第二行是待办）。你需要拆开分别执行脚本！一切处理都要在底层安静完成。

---

## 🎯 标签与项目提取示例

输入：`待办: 预定机票 #生活 【旅行】` 

应对行为：
1. **提取正文**："预定机票"
2. **提取参数**：`--tag 生活` 和 `--project 旅行`
3. **最终命令**：`python3 '{SKILL_DIR}/scripts/add_todo.py' "预定机票" --tag 生活 --project 旅行`

一切顺利后，请回复："已记录到 Notion ✅"（可简单概括录入了什么类型）。