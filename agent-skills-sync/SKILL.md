---
name: agent-skills-sync
description: 管理本机多个 AI agent（WorkBuddy 国内版/海外版 / Claude Code / Codex / ZCode / Gemini CLI / Antigravity）共享用户级技能的单一真相源。当用户问「技能怎么同步到所有 agent」「加一个技能到所有 agent」「各 agent 技能不一致」「某个 agent 里 `/` 看不到技能」「junction 链路断了」，或需要诊断/修复技能目录结构时使用。
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
1. 在仓库建 `<skill>/SKILL.md`（frontmatter 必须有 `name` 与 `description`，`name` 与目录名一致）
2. 进了 README 表格（CI 强制双向校验）
3. `python scripts/skillsync.py link --apply` 分发到各 agent
4. **Antigravity 侧**：因 `~/.gemini/config/skills.json` 已直挂主库根目录，主库新增技能重载窗口或新开会话即可自动识别；若新增技能未建在主库（放置在外部独立目录），必须同步加到 `~/.gemini/config/skills.json` 的 `entries` 列表中。
5. `python scripts/check_consistency.py` 校验后提交

**从某 agent 目录吸收新技能**：`python scripts/skillsync.py adopt --only <skill> --apply`。

## 已知坑位

**Antigravity Windows 扫描机制**：Antigravity 底层在 Windows 下通过标准 `io/fs` 扫描，会跳过 `~/.gemini/config/skills/` 内部的二级 Junction 目录。因此 Antigravity 统一采用原生声明式配置 `~/.gemini/config/skills.json` 直接挂载主库真实路径，绕过子目录 Junction 限制。

**链式链接**：junction 指向另一个 agent 的目录（如 workbuddy→zcode→codex）会造成三层套娃，中间一层挪动全断。所有链接必须直接指向仓库。`doctor` 会把这类问题全部列出。

**冲突保护**：若某 agent 目录的真实副本与仓库正文（SKILL.md 去掉 frontmatter 后）不同，`link` 会自动隔离该技能，既不分发也不回链——因为分发会把仓库版本塞给别的 agent，回链会丢掉 agent 侧的改动。这类必须人工定夺。

**漂移多是渠道差异，不是内容冲突**：zcode 的 skillhub 会往 frontmatter 注入 `display_name`/`visibility`/`metadata`，Claude 侧多 `locales/zh-CN.json`，还有完整仓库 vs 精简发布版之差（`fixtures`/`tests`/`__pycache__`）。`scan` 按「正文是否相同」分类，正文相同即可安全合并。

**旧脚本已废弃**：`scripts/sync_zcode_skills.py` 是单向复制（先 rmtree 仓库目录再 copytree），在 junction 布局下方向相反会覆盖仓库，已内置拒绝执行的硬保护。

**跨盘 junction**：仓库在 D 盘、agent 目录在 C 盘，属正常用法，已实测可读。D 盘不可用时 agent 会扫不到技能。
