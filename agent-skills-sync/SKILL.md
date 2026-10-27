---
name: agent-skills-sync
description: 管理本机多个 AI agent（WorkBuddy 国内版/海外版 / Claude Code / Codex / ZCode / Gemini CLI / Antigravity）共享用户级技能的单一真相源。当用户问「技能怎么同步到所有 agent」「新建一个技能」「写个 skill」「这个技能该放哪」「加一个技能到所有 agent」「各 agent 技能不一致」「某个 agent 里 `/` 看不到技能」「junction 链路断了」，或需要诊断/修复技能目录结构时使用。新建技能前必读：技能只能建在主库，不能用 skill-creator 的默认路径。
agent_created: true
---

# 多 Agent 技能同步

本机所有 agent 的用户级 skills 目录，通过 Windows 目录联结（junction）指向同一个仓库。**仓库是唯一真相源**：改仓库里的文件，所有 agent 立即生效，不需要任何同步命令。

## 架构

```
D:\Project\workspace\my_github\my-skills\   ← 唯一真相源（git，公开仓库）
        │
        ├── ~/.workbuddy/skills/<skill>      ← junction（国内版）
        ├── ~/.workbuddy-ai/skills/<skill>   ← junction（海外版，独立配置目录）
        ├── ~/.claude/skills/<skill>         ← junction
        ├── ~/.codex/skills/<skill>          ← junction
        ├── ~/.zcode/skills/<skill>          ← junction
        ├── ~/.gemini/config/skills/<skill>  ← junction (Gemini CLI)
        └── ~/.gemini/config/skills.json     ← Antigravity 官方原生直挂主库
```

**WorkBuddy 国内版与海外版是两个独立安装**，配置目录分别是 `~/.workbuddy` 和 `~/.workbuddy-ai`（程序在 `D:\Software\WorkBuddy` 与 `D:\Software\New folder\WorkBuddyAI`），技能目录互不相通，必须各自纳入 `agents` 配置。

第三方技能（Kimi/Wind 官方、Academic pack、FBSir 等）同样落在该仓库，但由 `.gitignore` 的 `skillsync` 标记区块排除，不入公开仓库、不参与 README 校验。

## 为什么这样设计（改动前必读）

所有决策都收敛到同一件事：**消除副本**。技能不能有副本，所以用链接；规则不能有副本，所以用分发；`.gitignore` 与 README 的一致性靠标记区块，不靠人工核对。

起点不是「同步做得不够好」。复制模式靠「记得同步」维持，而人会忘、脚本会漏——实测 79 份真实副本、29 个技能存了多份，能完全对上的只有 5 个。这是模式问题，不是执行问题。所以选的是**共享**而非**同步器**：不是让同步更可靠，而是让「同步」这个动作不存在。

| 判断 | 选了什么 | 选反了的代价 |
|---|---|---|
| 主库 | 用已有的 `my-skills`，不另建目录 | 公开仓库→第三方必须隔离；在 D 盘→C 盘重置不丢；已按 public/personal 分过类→「什么该入库」有现成标准。另建目录这些约束一个都不存在 |
| 链接粒度 | 逐技能 junction | 整目录链接省事，但每个 agent 被迫看到全部技能、agent 自己装的会混进主库、没法按 agent 过滤 |
| 冲突 | 隔离待人工定夺，不强行合并 | 取「最全的一份」可能覆盖某个 agent 里更新的改动；隔离才让首次迁移安全落地 |

**边界**：一台机器、用户级技能、你能控制所有 agent 的目录布局。多机、团队、项目级技能都要换方案。

**当前残留（2026-10-27 归集后）**：链式 junction 9 → 2，多副本技能 11 → 2。剩下这两个是**第三方技能** `etfirst`、`neodata-financial-search`，差异在渠道参数——`sub_channel` 分别是 `mimo` 和 `workbuddy`，Python 路径也随之不同，不是版本新旧。**已决定让各 agent 各自保留、不共享**，记在 baseline 的 `intentional` 里（设计如此，不算欠账）。其余 59 份副本集中在未纳入主库的第三方技能上，属正常。

## 命令

工具在仓库内 `scripts/skillsync.py`，配置在 `~/.agents/skillsync.json`。

```bash
python scripts/skillsync.py status        # 每个 agent 每个技能的状态矩阵
python scripts/skillsync.py scan          # 多份副本的漂移分类报告
python scripts/skillsync.py doctor        # 断链、链式嵌套、主库含链接等结构问题
python scripts/skillsync.py adopt         # 收编散落副本进仓库（默认 dry-run）
python scripts/skillsync.py link          # 把仓库技能分发到各 agent（默认 dry-run）
python scripts/skillsync.py gitignore     # 刷新 .gitignore 第三方区块
```

安全约定：`adopt` / `link` 默认只预演，加 `--apply` 才动文件；源目录只移动到 `_skillsync_backup/<时间戳>/`，绝不删除；删链接用 `os.rmdir`，不会碰目标内容。

## 日常流程

**改技能**：直接编辑仓库里的文件，保存即生效，无需任何命令。

**加技能**：

> **不要用内置 `skill-creator` 的默认路径**（`~/.codebuddy/skills/`）——该目录不在任何 agent 的扫描范围内，建了没人看得见。技能一律建在 `<主库>/<skill-name>/`，再用 `link --apply` 分发。

1. 在仓库建 `<skill>/SKILL.md`（frontmatter 必须有 `name` 与 `description`，`name` 与目录名一致）
2. 进了 README 表格（CI 强制双向校验）
3. `python scripts/skillsync.py link --apply` 分发到各 agent
4. **Antigravity 侧**：因 `~/.gemini/config/skills.json` 已直挂主库根目录，主库新增技能重载窗口或新开会话即可自动识别；若新增技能未建在主库（放置在外部独立目录），必须同步加到 `~/.gemini/config/skills.json` 的 `entries` 列表中。
5. 提交（`.git/hooks/pre-commit` 会自动跑一致性与结构闸门，见下节）

**从某 agent 目录吸收新技能**：`python scripts/skillsync.py adopt --only <skill> --apply`。

## 提交闸门

约定破了问题会立刻回来，所以把检查挂在提交上，而不是靠事后 `scan` 发现。`scripts/precommit.py` 装在 `.git/hooks/pre-commit`：

- `check_consistency.py` 失败 → **拒绝**（README 与目录必须双向一致）
- 报出**新增**链式 junction → **拒绝**（baseline 的 `intentional` 是设计上不共享的第三方技能，`chained` 是待修欠账、目标为空）
- 真实副本数上涨 → 只**警告**（归集要人工判断，不该堵住提交）

判定原则是**只拦新增问题，不为历史欠账买单**——否则 76 份副本和 9 项链式会让任何提交都过不去。

```bash
cp scripts/git-hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
python scripts/precommit.py --update-baseline   # 修好欠账后刷新豁免清单（只允许变短）
git commit --no-verify                          # 临时跳过
```

## 已知坑位

**Antigravity Windows 扫描机制**：Antigravity 底层在 Windows 下通过标准 `io/fs` 扫描，会跳过 `~/.gemini/config/skills/` 内部的二级 Junction 目录。因此 Antigravity 统一采用原生声明式配置 `~/.gemini/config/skills.json` 直接挂载主库真实路径，绕过子目录 Junction 限制。

**链式链接**：junction 指向另一个 agent 的目录（如 workbuddy→zcode→codex）会造成三层套娃，中间一层挪动全断。所有链接必须直接指向仓库。`doctor` 会把这类问题全部列出。

**冲突保护**：若某 agent 目录的真实副本与仓库正文（SKILL.md 去掉 frontmatter 后）不同，`link` 会自动隔离该技能，既不分发也不回链——因为分发会把仓库版本塞给别的 agent，回链会丢掉 agent 侧的改动。这类必须人工定夺。

**归集已有的真实副本**（`link` 会跳过它们，得手工做）：先比对 mtime——副本早于主库 = 主库更新，可安全替换；再把副本移进 `_skillsync_backup/<时间戳>/<agent>/`，原位 `mklink /J` 指向主库。**判断 junction 是否合规不能用 `realpath`**：它会把整条链解析到底，`workbuddy → zcode → 主库` 这种两跳看起来和直连一样。要比对 `os.readlink()` 拿到的**直接目标**。

**漂移多是渠道差异，不是内容冲突**：zcode 的 skillhub 会往 frontmatter 注入 `display_name`/`visibility`/`metadata`，Claude 侧多 `locales/zh-CN.json`，还有完整仓库 vs 精简发布版之差（`fixtures`/`tests`/`__pycache__`）。`scan` 按「正文是否相同」分类，正文相同即可安全合并。

**旧脚本已废弃**：`scripts/sync_zcode_skills.py` 是单向复制（先 rmtree 仓库目录再 copytree），在 junction 布局下方向相反会覆盖仓库，已内置拒绝执行的硬保护。

**跨盘 junction**：仓库在 D 盘、agent 目录在 C 盘，属正常用法，已实测可读。D 盘不可用时 agent 会扫不到技能。
