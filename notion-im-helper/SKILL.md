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

## 🧩 语义级智能匹配与调用表（无需死板校验格式！）

> **⚠️ 绝对最高优先级匹配原则：意图 > 格式**
> 只要用户的输入**在语义上（大意上）**符合下面的某一个功能，请**大胆地认定其意图！** 
> 用户的消息可能非常随意（例如：`笔记：`是中文冒号，`笔记 `只有空格，`笔记`紧跟文字，`flash，`用逗号）。**绝对不准向用户挑错“您的标点符号使用的是中文”之类的话**。你要做的就是：剥离掉所有可能存在的触发词成分，提取最纯净的核心正文，并将提取出的 `#标签` 和 `【项目】` 通过参数传入相应脚本。

| 用户的口语化/语义特征 | 用户可能的随意输入示例 | 对应脚本调用格式 |
|-------------------|--------------------|--------------|
| **(默认) 日常/日记** | `今天被老板骂了QAQ` | `python3 '{SKILL_DIR}/scripts/add_record.py' "正文" --type diary` |
| **学习/体系化笔记** | `笔记：Python内存分代...` / `学习-Git原理` | `python3 '{SKILL_DIR}/scripts/add_record.py' "正文" --type note` |
| **闪念/突发奇想** | `flash，刚想到个好点子` / `闪念: 买一把新伞` | `python3 '{SKILL_DIR}/scripts/add_record.py' "正文" --type flash` |
| **产品灵感/想法** | `idea 可以做个记账工具` | `python3 '{SKILL_DIR}/scripts/add_record.py' "正文" --type idea` |
| **提问/遇到问题** | `疑问：为什么前端又跨域了` | `python3 '{SKILL_DIR}/scripts/add_record.py' "正文" --type question` |
| **复盘/周月总结** | `本周学习小结：...` | `python3 '{SKILL_DIR}/scripts/add_record.py' "正文" --type summary` |
| **日常购物/待办** | `待办事项 洗车、买菜` / `todo：交电费` | `python3 '{SKILL_DIR}/scripts/add_todo.py' "任务1" "任务2"` |
| **明确的任务** | `task：写完周会报告` | `python3 '{SKILL_DIR}/scripts/add_todo.py' "正文" --type task` |
| **已搞定的任务** | `√ 报销 发票` / `✓做完PPT了` | `python3 '{SKILL_DIR}/scripts/add_todo.py' "纯任务名" --done` |
| **保存网页链接** | `帮我存一下这个网址 https://...` / `直接发单链接` | `python3 '{SKILL_DIR}/scripts/add_link.py' "网址URL"` |
| **名言/引用摘抄** | `摘抄：人生如逆旅...` / `> 一万年太久` | `python3 '{SKILL_DIR}/scripts/add_quote.py' "纯引用文字"` |
| **搜寻过往卡片** | `帮我搜一下缓存相关的笔记` | `python3 '{SKILL_DIR}/scripts/search_notes.py' "关键字"` |

*(注：绝不要往任何脚本传 `--claw` 或 `--source`，该功能已彻底下线弃用)*

### 🏗️ 排版类指令（H1/H2、列表等）：多行混合输入时调用

除了上述根据语义录入的 Record（记录型）以外，当遇到长篇或明确结构化的指令时：
| 排版结构特征 | 示例 | 对应脚本调用格式 |
|-----------|------|--------------|
| 一/二/三级标题 | `*周报` 或 `***小结` | `python3 '{SKILL_DIR}/scripts/add_heading.py' <级别1-3> "标题"` |
| 无序列表项 | `- 买苹果` | `python3 '{SKILL_DIR}/scripts/add_list.py' bullet "文本"` |
| 有序列表项 | `1. 第一步` | `python3 '{SKILL_DIR}/scripts/add_list.py' number "文本"` |
| 下拉折叠列表 | `下拉：我的计划` | （通过管道传规范化 JSON 至 `'{SKILL_DIR}/scripts/add_toggle.py'`） |

### 🤖 智能瞎猜与多行解析（极其重要）
1. **完全没有触发前缀的随意短句**：发挥语义理解能力盲猜！比如全是琐碎感慨就是 `--type diary`，是长篇知识就是 `--type note`。
2. **多行混合文本**（甚至夹杂了标题和待办）：你需要将它们拆开，按顺序多次独立静默调用不通脚本！不要让用户感觉你在“分心”，一切处理都要在底层安静完成，最后给一个整合回复即可。

---

## 🎯 标签与项目提取示例

输入：`待办: 预定机票 #生活 【旅行】` 

应对行为：
1. **提取正文**："预定机票"
2. **提取参数**：`--tag 生活` 和 `--project 旅行`
3. **最终命令**：`python3 '{SKILL_DIR}/scripts/add_todo.py' "预定机票" --tag 生活 --project 旅行`

一切顺利后，请回复："已记录到 Notion ✅"（可简单概括录入了什么类型）。