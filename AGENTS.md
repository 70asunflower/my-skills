# 本机技能库使用规则

本文件是**唯一权威源**。修改这里，然后运行 `python scripts/skillsync.py rules --apply`
把下面标记区块的内容分发到各 agent 的全局指令文件。

不要直接去改各 agent 的 `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 里的同名区块——下次分发会被覆盖。

<!-- BEGIN skillsync-rules -->
## 用户级技能库

本机所有 AI agent 的用户级技能共享同一个仓库：`D:\Project\workspace\my_github\my-skills`。
各 agent 的 skills 目录里每一项都是指向该仓库的目录联结（junction），不是副本。

- **修改技能**：直接改。改 agent 目录还是改仓库，都是同一份文件。
- **新增技能**：必须建在仓库里（`<skill>/SKILL.md`，frontmatter 需 `name` 与 `description`，`name` 与目录名一致）。不要在你的 skills 目录下新建真实目录——那个父目录是真实的，新建出来的会脱离仓库，其他 agent 看不到。
- **第三方技能**（Kimi/Wind 官方、Academic pack、FBSir 等）由 `.gitignore` 的 `skillsync` 标记区块排除，不要 `git add`。
- **不要复制技能**。副本会立刻开始漂移。
- WorkBuddy 国内版（`~/.workbuddy`）与海外版（`~/.workbuddy-ai`）是两个独立安装，技能互不相通，两边都要维护。

## 维护技能：更新即重构，禁止末尾追加

技能是**每次触发都整篇读进上下文**的，篇幅直接等于成本。所以「更新技能」不等于「在文件末尾再补一段」：

- **默认动作是重构，不是新增。** 新知识先判断归属：替换旧条目 / 合并进既有条目 / 确实开了新主题才允许新增条目。
- **每次更新都要能回答「删了什么」。** 净增而不删，就是没重构。该删的典型：版本变更日志与升级过程、事故经过的叙事（只留规则）、跨技能重复的规则、对执行无帮助的日期与出处标注。
- **同一规则只在一个技能里维护**，其余技能写一行指针（例：公式规则归 `siyuan-markdown-formula-formatter`，`siyuan-kernel-ops` 只留指针）。两处都写，迟早各自漂移。
- **瘦身顺序**：删叙事与变更日志 → 跨技能去重 → 最后才把代码抽到 `scripts/`。反过来先动代码会破坏可用性。
- **长技能（>300 行）**优先把细节拆到 `scripts/` 或子文件，正文只留判断规则、症状索引与指针。

## 工具

在仓库目录下运行，配置在 `~/.agents/skillsync.json`：

```bash
python scripts/skillsync.py status        # 各 agent 每个技能的链接状态
python scripts/skillsync.py doctor        # 断链、链式嵌套等结构问题
python scripts/skillsync.py scan          # 多副本漂移报告
python scripts/skillsync.py link --apply  # 把仓库技能分发到各 agent
python scripts/skillsync.py adopt --only <skill> --apply   # 从某 agent 吸收技能进仓库
python scripts/skillsync.py rules --apply # 把本规则块分发到各 agent 全局文件
```

`adopt`、`link`、`rules` 默认 dry-run，不加 `--apply` 不会动任何文件。收编或分发时会自动隔离「正文冲突」的技能（某 agent 的副本 SKILL.md 正文与仓库不同），这类既不分发也不回链，须人工定夺版本。

## 排障

- `find -name SKILL.md` 不跟随 junction，会误报技能丢失。要判断技能是否可用，看该目录项的 `SKILL.md` 能否直接读取。
- 判断某项是否已被纳入管理：**不能只看 `os.path.isjunction()`**。链式 junction（`workbuddy/x → zcode/x → 真实目录`）同样返回 True，但它并没有指向主库。也不能用 `os.path.realpath()`——它会把整条链解析到底，两跳和直连看起来一模一样。要比对 `os.readlink()` 返回的**直接目标**是否等于主库路径。`os.path.islink()` 对 junction 返回 False，不能用来判断。
- 提交前检查已自动化：`.git/hooks/pre-commit` 会跑 README↔目录一致性，并拦截**新增**的链式 junction（历史欠账记在 `scripts/skillsync-baseline.json` 豁免）。机制细节与设计理由见 `agent-skills-sync` 技能。

## 写长文

报告、方案、论文、正式文档、README、汇报材料等长文本，产出草稿后必须过一遍 `humanizer-zh` 技能再交付，去掉模板化表达、套话与 AI 腔，同时保留事实、确定程度和作者声音。润色已有文本同样适用。
<!-- END skillsync-rules -->
