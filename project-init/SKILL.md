---
name: project-init
description: 项目初始化/接管/升级与 Agent 行为规范生成器 + 巡检修复器。init：git 初始化 + 规范目录（docs 正式文档、code 正式代码与测试、tmp 临时区）+ AGENTS.md 唯一规范来源 + 7 个 agent 入口（Claude/Gemini/Qwen/Cursor/Windsurf/Cline/Copilot）+ 程序项目脚手架（PRD/Design/TDD/开发进度台账、features 功能文档、README、assets）。adopt：接管已有散乱项目，输出迁移建议、可执行。upgrade：规范模板升级 diff。check：只读巡检（AI 痕迹、版本副本、日志、台账与功能文档状态一致性、顶层文档齐全性等）+ --fix 无争议自动修复 + --scan 批量巡检。当用户说"项目初始化、建个新项目、规范 agent 行为、生成 AGENTS.md、开发流程规范、命名规范、开发进度、功能测试、接管旧项目、整理项目、规范升级、检查项目规范、批量巡检、有没有 AI 痕迹、项目是不是乱了"等时使用，即使没明说"初始化"；agent 自己进入已初始化项目收工前也应触发自检。
---

# project-init —— 项目初始化/接管/升级与 Agent 行为规范

在目标项目文件夹一键完成：git 初始化 → 规范目录结构（docs / code / tmp）→ 多 agent 行为规范文件 → 程序项目开发流程脚手架（PRD / Design / TDD / 开发进度台账）。附带巡检（--fix 自动修复、--scan 批量）。脚本仅用 Python 标准库。

## 快速用法（优先用脚本，不要手工逐步执行）

### 场景一：初始化新项目

```bash
python "<本skill目录>/scripts/init_project.py" "<项目目录>"
# 常用变体:
#   --stack "Python 3.12 + FastAPI"   技术栈写入 AGENTS.md 头部
#   --for minimal | --for claude,cursor
#            （可选: claude,gemini,qwen,cursor,windsurf,cline,copilot）
#   --no-software     纯文档项目：跳过程序项目脚手架
#   --force / --no-git
```

脚本依次执行：git init（main 分支）→ docs/（含 assets/、releases/ 由规范约定）、code/、tmp/ → .gitignore（忽略 tmp/ 等）→ 渲染 AGENTS.md（唯一规范来源，头部含技术栈与规范版本）→ 7 个 agent 薄入口（只指向 AGENTS.md）→ 程序项目脚手架（默认，`--no-software` 跳过）：docs/PRD.md、Design.md、TDD.md、开发进度.md（各配 .log.md）+ docs/features/ → README.md → 首次提交（git 身份未配置则跳过）。已存在文件默认跳过；`python` 不可用时用 `py`。

### 场景二：接管已有散乱项目

```bash
python init_project.py "<项目目录>" --adopt          # 补规范结构 + 输出迁移建议（不动文件）
python init_project.py "<项目目录>" --adopt --apply  # 执行无争议移动（docs/code/tmp 三类）
```

建议按扩展名启发式分类（文档→docs/，代码→code/，数据媒体→tmp/，配置保留根目录，其余标"需人工判断"）。**--apply 只移动前三个无争议类，「需人工判断」项必须与用户逐个确认**。移动后：为移入 docs/、code/ 的文件补 .log.md（可用 check --fix），再 git commit。

### 场景三：规范模板升级

```bash
python init_project.py "<项目目录>" --upgrade   # 打印 diff，新模板写入 tmp/AGENTS.new.md
```

逐段与用户核对后手动合并进 AGENTS.md（规范文件修改须经所有者确认），合并后删除临时文件并提交。不自动覆盖。

### 场景四：规范巡检（只读 / 修复 / 批量）

```bash
python check_project.py "<项目目录>"              # 只读巡检
python check_project.py "<项目目录>" --fix        # + 无争议自动修复
python check_project.py --scan "<工作区根>" [--depth 2]   # 批量巡检所有含 AGENTS.md 的项目
```

- **[E] 错误**：版本副本增殖（`_v2`/`final`/`最终`/`copy` 等）、docs/ Markdown 的 AI 痕迹（对话腔、AI 声明、emoji）、正文内"修订历史"章节、code/ 注释中的 AI 痕迹、台账与功能文档状态不一致。有 E 则退出码 1。
- **[W] 警告**：根目录散落文件、缺同名 .log.md 或日志空壳、tmp/ 被 git 跟踪、程序项目缺四份顶层文档、状态非「待办」的功能缺功能文档或缺状态字段、docs//code/ 存在未跟踪正式文件、docs/ 非 UTF-8 编码的 Markdown、命名不规范（占位名、空格/特殊字符、疑似 (1) 重复副本、文件名含日期）。
- **[I] 提示**：未提交变更、tmp/ 积压（>30 个文件）。
- **豁免**：`docs/releases/` 为交付快照区，豁免 AI 痕迹、日志配对与版本副本检查。
- **--fix 只做无争议修复**：补缺失/空壳日志、从模板补缺失顶层文档、按台账补功能文档骨架（各配日志）。AI 痕迹、版本副本、状态冲突等须人工。

## 初始化之后（触发本 skill 的 agent 必做）

1. 读取项目内生成的 `AGENTS.md` 全文，并在**本会话后续所有工作中严格遵守**。
2. 向用户简报：建了哪些目录与文件；规范五条核心规则各一句话（存放 / 迭代 / 日志 / 无 AI 痕迹 / 开发流程，见下）。

## 巡检之后的修复纪律

- E 类应修复：状态不一致 → 与用户核对哪边是真，改正错误一方并记日志；AI 痕迹 → 改写为正式书面表达；版本副本 → 与用户确认保留哪份，合并回主文件后 `git rm` 并记日志。
- 涉及删除、合并、重命名的操作属破坏性操作：先列清单征得用户同意，执行后在对应 .log.md 记录。
- W / I 类：报告并给建议，用户同意后再动（补日志类可直接用 --fix）。

## 规范要点（与生成的 AGENTS.md 一致，供 agent 快速对照）

- **存放**：正式文档进 `docs/`，正式代码与测试（`code/tests/`）进 `code/`，其余一切临时产物（含一次性脚本）进 `tmp/`（git 忽略）；根目录不放散文件；配图进 `docs/assets/`；交付快照进 `docs/releases/`（豁免禁副本与日志）。
- **迭代**：就地修改原文件，禁版本副本；历史交给 git。
- **命名**：见名知义，禁占位名（新建/未命名/untitled/aaa/123 等）；只用中文、字母、数字、连字符、下划线；正式文件名不带日期与版本（`docs/releases/` 快照须含版本号）；文档用中文名，代码按语言社区惯例并全项目统一。
- **日志**：每正式文件配同名 `<主名>.log.md`，逐条追加"时间/修改者/摘要/原因"；根目录规范文件、.gitignore、releases 快照无需日志。
- **无 AI 痕迹**：docs 内容与 code 注释禁对话腔、AI 声明、emoji、正文修订历史章节、占位残留。
- **开发流程**（程序项目）：四份顶层文档缺一不可（PRD 做什么为什么 / Design 怎么做 / TDD 技术方案 / 开发进度台账=唯一进度事实来源，顶部有「当前功能」行）；收到多功能需求先把全部登记为「待办」，一次只开发一个：`待办→开发中→待测试→测试通过→已审核`，测试未通过登记「缺陷记录」表、缺陷不关闭不得回到测试通过也不得开下一个功能；每功能一份 `docs/features/<功能名>.md`（功能说明/实现思路/测试情况/审核记录）；每个功能须人工审核，agent 不得自行标记「测试通过」「已审核」。

## 自定义

- 改规范内容：`assets/AGENTS.template.md`（{{PROJECT_NAME}}/{{TECH_STACK}}/{{VERSION}} 占位符），改后递增 init_project.py 的 `VERSION`，已初始化项目用 `--upgrade` 同步。
- 改程序项目文档模板：`assets/software/`。
- 改检查规则与白名单：`check_project.py` 顶部常量（ALLOWED_ROOT、VERSIONISH、短语表、CODE_EXTS、REQUIRED_SW_DOCS、SKIP_DIRS）。
- 改接管启发式：`init_project.py` 的 KEEP_ROOT / DOC_EXTS / CODE_EXTS / TMP_EXTS。
- 新增 agent 适配：`init_project.py` 的 `ADAPTERS` 字典加一个"指向 AGENTS.md"的入口。

## 自测

```bash
python scripts/init_project.py /tmp/pi-test && python scripts/check_project.py /tmp/pi-test   # 应无 E/W
python scripts/init_project.py /tmp/pi-mess --adopt          # 散乱目录应输出迁移建议，--apply 执行
python scripts/check_project.py --scan /tmp --depth 1        # 批量巡检
python scripts/init_project.py /tmp/pi-test --upgrade        # 同版本应报"已是最新"
```

违规样例：docs/ 放 `报告_v2.md`（含对话腔）应报 E 副本+E 痕迹+W 缺日志；台账登记状态「测试通过」但功能文档写「待办」应报 E 状态不一致；`code/main.py` 注释含"作为一个AI"应报 E 注释痕迹；`docs/新建文档 (1).md`、`docs/20260928-报告.md` 应报 W 命名不规范。
