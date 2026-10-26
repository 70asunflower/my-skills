# WorkBuddy / ZCode Custom Skills

我的 WorkBuddy / ZCode 自定义 Skills 集合。

## Skills 列表

### 通用技能 `public` — 适合所有人使用

| Skill | 描述 |
|-------|------|
| [md-to-70asunflower-latex](./md-to-70asunflower-latex/) | 将 Markdown 技术博客转换为 70asunflower 风格的 LaTeX 文档，适配 Overleaf XeLaTeX 编译 |
| [md2docx-formal](./md2docx-formal/) | 将 Markdown 中文工程文档转换为规范排版的 Word（A4、篇/章/节标题层级、1.5 倍行距、自动目录、页眉页脚、GB/T 7714 引用上标），并支持源文档一致性审查 |
| [message-friendly](./message-friendly/) | 微信/IM 排版净化神器，自动拦截大模型的 Markdown 乱码，转化为带 Emoji 分层、二维表降级和极佳留白的呼吸感纯文本 |
| [notion-im-helper](./notion-im-helper/) | 通过 IM 向 Notion 添加内容，支持闪念速记、待办清单、标题、引用、列表等多种格式 |
| [notebook-patching](./notebook-patching/) | Jupyter Notebook (.ipynb) 与 IDE 打开状态下的受限文件快速安全修改工作流，规避内联转义与 Auto-Save 内存覆盖冲突 |
| [feishu-bot-config](./feishu-bot-config/) | 飞书机器人配置管理工具，自动化添加、管理和排查飞书机器人集成 |
| [infographic](./infographic/) | 从文章或 URL 生成深色杂志风格信息卡 HTML，支持导出 PNG 图片 |
| [ai-tutorial-pipeline](./ai-tutorial-pipeline/) | 用网页版 AI 按大纲逐章生成高质量教程并自动入库思源笔记，含浏览器接管、表格/公式格式校验 |
| [doc-plain-zh](./doc-plain-zh/) | 中文文档可读性转换：拗口 → 通顺，只改表达、不改逻辑与事实，保持书面正式 |
| [jetson-thor-mem-diag](./jetson-thor-mem-diag/) | Jetson AGX Thor（Blackwell 统一内存）"内存被占满却查不到进程"的诊断与回收手册 |
| [paper-figures](./paper-figures/) | 学术图表统一入口：matplotlib 投稿矢量图 / Origin 可编辑直通 / python-pptx 示意图三条管线按用途路由；含期刊海报与图文摘要模板、色盲安全检查、视觉一致性校验 |
| [project-init](./project-init/) | 项目初始化 + 多 agent 规范生成（AGENTS.md + 7 个 agent 入口）+ 巡检修复器 |
| [project-review](./project-review/) | 项目六维审查评分 + 审计报告，与 project-init 互补 |
| [siyuan-backup-sync](./siyuan-backup-sync/) | 思源笔记数据仓库的 Git 备份/同步工作流 |
| [siyuan-kernel-ops](./siyuan-kernel-ops/) | 通过思源内核 HTTP API 安全检索/读写/批量处理笔记库，含端口漂移、上传、索引滞后等坑位手册 |
| [siyuan-markdown-formula-formatter](./siyuan-markdown-formula-formatter/) | 思源专用 Markdown/LaTeX 公式排版规范，彻底解决公式渲染失败 |
| [strict-docx-audit](./strict-docx-audit/) | docx 转换后的质量闸：12 项结构与排版检查 |
| [snap](./snap/) | 零依赖页面截图/体检/像素对比 CLI：无头 Chrome 一条命令截图（整页/元素/区域/高清），--audit 程序化检坏图溢出裁切，--diff 视觉回归；agent 确认页面渲染效果首选 |
| [svg-diagram-pipeline](./svg-diagram-pipeline/) | SVG 交互示意图 → 无头 Chrome 渲染 PNG → 插入思源笔记的完整管线，含 MOSFET 电路符号语法 |
| [agent-skills-sync](./agent-skills-sync/) | 多 agent（WorkBuddy/Claude/Codex/ZCode/Gemini）共享用户级技能的单一真相源：junction 分发、状态矩阵、漂移分类与冲突保护 |

### 个人工作流 `personal` — 包含个人特定配置，他人无需安装

| Skill | 描述 |
|-------|------|
| [captain-resource](./captain-resource/) | 资源入库助手，将 URL/文章/工具等添加到 ai-learning-journey、embodied-ai-learning、ic-chip-design-learning 三个学习仓库 |
| [investment-analysis](./investment-analysis/) | 个人投资分析方法论与操作规程（林奇六分类 + 预测档案系统），含个人工作区路径 |
| [trek-mcp-ops](./trek-mcp-ops/) | 自部署 TREK 旅行规划器（Docker + 内置 MCP 135 工具）的启停/建行程/排障手册，含本机端口与代理配置 |
| [xhs-pipeline](./xhs-pipeline/) | 小红书信息收集流水线（profile 驱动：搜索/抓取/审读/合并入库），依赖本机浏览器登录态 |

## 标签说明

- `public` — 通用技能，不依赖特定配置，任何人都可以使用
- `personal` — 包含个人 API Key、工作流、习惯等定制化内容，**其他人不需要安装**

## 使用方式

把 skill 文件夹复制到对应 agent 的 skills 目录即可使用。本机已改为目录联结（junction）方式，见下一节。

- WorkBuddy：`~/.workbuddy/skills/`
- Claude Code：`~/.claude/skills/`
- Codex：`~/.codex/skills/`
- ZCode：`~/.zcode/skills/`
- Gemini CLI：`~/.gemini/config/skills/`
- Antigravity：`~/.gemini/config/skills.json`（原生声明式直挂主库，避开 Windows Junction 限制）

## 外部技能

除上表收录的自制技能外，本机还统一管理着一批外部技能——包括 `humanizer-zh`（去 AI 味润色，MIT，来自 op7418/Humanizer-zh）、`kimi-webbridge`（浏览器接管）、`mcporter`（MCP 调度）、`fireworks-tech-graph`（SVG 图形）等。它们以完全相同的 junction 方式分发到各 agent，但**不纳入本仓库版本控制**（见 `.gitignore` 的 `skillsync` 标记区块），只随目录存在于本机。

其中 `humanizer-zh` 已被定为**写长文时的固定动作**：报告、方案、论文、正式文档、README、汇报材料等长文本，产出草稿后过一遍该技能再交付。

这些技能在主库里的位置示意：

```
my-skills/
├── agent-skills-sync/     自制
├── siyuan-kernel-ops/     自制
├── humanizer-zh/          外部 · 去 AI 味润色（写长文必过）
├── kimi-webbridge/        外部 · 浏览器接管
└── mcporter/              外部 · MCP 调度
```

## 与本机各 agent 的技能目录保持同步

本机各 agent 的 skills 目录通过 Windows 目录联结指向本仓库（Antigravity 通过 `skills.json` 原生直挂），**本仓库是唯一真相源**：直接编辑这里的文件，所有 agent 立即生效，不再需要任何同步命令。

```bash
# 诊断（只读）
python ~/.agents/skillsync.py status     # 每个 agent 每个技能的链接状态
python ~/.agents/skillsync.py doctor     # 断链、链式嵌套等结构问题
python ~/.agents/skillsync.py scan       # 多份副本的漂移报告

# 在本仓库新增技能目录后，分发到各 agent
python ~/.agents/skillsync.py link --apply

# 提交前校验（CI 同款）
python scripts/check_consistency.py
```

本仓库是公开仓库，只收录自制技能。第三方技能（Wind/Kimi 官方、Academic pack、FBSir 等）由 skillsync 收编到本机、在 `.gitignore` 的 `skillsync` 标记区块中排除，随目录存在但不入库，也不参与 README 校验。

`scripts/sync_zcode_skills.py` 已废弃并内置拒绝执行的保护——旧逻辑是「先删除仓库目录、再从 agent 目录复制」，在 junction 布局下方向相反，会把仓库内容覆盖掉。
