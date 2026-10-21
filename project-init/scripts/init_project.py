#!/usr/bin/env python3
"""project-init: 初始化/接管/升级项目 —— git + 规范目录 + 多 agent 行为规范 + 程序项目文档脚手架。

用法:
    python init_project.py [目标目录] [选项]              初始化新项目
    python init_project.py [目标目录] --adopt [--apply]   接管已有项目：补规范结构，输出/执行迁移建议
    python init_project.py [目标目录] --upgrade           规范模板升级：生成 diff 与新模板供人工合并

选项:
    --name NAME    项目名（默认取目录名）
    --stack DESC   技术栈描述，写入 AGENTS.md（如 "Python 3.12 + FastAPI"）
    --for SPEC     agent 适配范围: all(默认) | minimal | 逗号分隔列表
                   可选: claude,gemini,qwen,cursor,windsurf,cline,copilot
    --no-software  不生成程序项目脚手架（PRD/Design/TDD/开发进度 及 features/）
    --force        覆盖已存在的规范文件
    --no-git       跳过 git init
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

VERSION = "1.2.0"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "AGENTS.template.md"
SOFTWARE_TPL_DIR = SKILL_DIR / "assets" / "software"

GITIGNORE = """\
# tmp 临时区不入库
tmp/
# 操作系统垃圾
Thumbs.db
desktop.ini
.DS_Store
# Office 锁文件
~$*
# 常见运行产物
__pycache__/
*.pyc
.venv/
node_modules/
dist/
build/
"""

# 各 agent 入口共用的正文：只做一件事——指向 AGENTS.md，保证规范只有这一个来源
POINTER_BODY = (
    "# 项目规范入口\n\n"
    "开始本项目任何工作前，先完整阅读项目根目录的 `AGENTS.md`——"
    "它是本项目全部协作规范的唯一来源，必须严格遵守。\n"
)

ADAPTERS: dict[str, dict[str, str]] = {
    "claude": {
        "path": "CLAUDE.md",
        "body": "# 项目规范入口\n\n@AGENTS.md\n\n> 上一行是 Claude Code 的导入语法。若导入未生效，请完整阅读项目根目录的 AGENTS.md 并严格遵守。\n",
    },
    "gemini": {"path": "GEMINI.md", "body": POINTER_BODY},
    "qwen": {"path": "QWEN.md", "body": POINTER_BODY},
    "cursor": {
        "path": ".cursor/rules/project-rules.mdc",
        "body": "---\nalwaysApply: true\n---\n\n" + POINTER_BODY,
    },
    "windsurf": {"path": ".windsurfrules", "body": POINTER_BODY},
    "cline": {"path": ".clinerules", "body": POINTER_BODY},
    "copilot": {"path": ".github/copilot-instructions.md", "body": POINTER_BODY},
}

# --adopt 迁移建议的启发式表
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git", ".idea", ".vscode"}
KEEP_ROOT = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "QWEN.md",
    ".gitignore", ".gitattributes", ".editorconfig", ".env", ".env.example",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "requirements-dev.txt",
    "poetry.lock", "uv.lock", "Pipfile", "Pipfile.lock", "environment.yml", "MANIFEST.in",
}
KEEP_PREFIX = ("README", "LICENSE", "CHANGELOG")
DOC_EXTS = {".md", ".docx", ".doc", ".pdf", ".pptx", ".ppt", ".xlsx", ".xls", ".epub", ".tex", ".bib", ".txt"}
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp", ".cc",
             ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".lua", ".r",
             ".sh", ".ps1", ".bat", ".sql", ".ipynb", ".vue", ".dart", ".m"}
TMP_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".csv", ".tsv", ".log", ".parquet",
            ".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".mp4", ".mov", ".wav", ".mp3"}

README_TPL = """# {name}

> 待补充：一句话说明本项目是什么、给谁用。

## 项目结构

| 位置 | 用途 |
|------|------|
| `docs/` | 正式文档（顶层文档、功能文档、交付物） |
| `code/` | 项目正式代码与测试 |
| `tmp/` | 临时区（不入库，随时可清空） |

## 协作规范

所有 AI Agent 与协作者开始工作前必须阅读 [AGENTS.md](AGENTS.md) 并严格遵守。
"""


def render_template(project_name: str, stack: str) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else "# 项目协作规范\n\n（模板缺失，请补全 assets/AGENTS.template.md）\n"
    return (tpl.replace("{{PROJECT_NAME}}", project_name)
               .replace("{{TECH_STACK}}", stack)
               .replace("{{VERSION}}", VERSION))


def run_git(repo: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout + p.stderr).strip()


def iter_entries(base: Path):
    """遍历目录产出文件（跳过 SKIP_DIRS 与隐藏目录）。"""
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            yield Path(dirpath) / fn


def adopt_plan(root: Path) -> list[dict]:
    """对根目录散落文件给出迁移建议：docs/ / code/ / tmp/ / ?（需人工判断）。"""
    plan: list[dict] = []
    for entry in sorted(root.iterdir()):
        nm = entry.name
        if entry.is_dir():
            if nm in ("docs", "code", "tmp") or nm.startswith(".") or nm in SKIP_DIRS:
                continue
            n = sum(1 for _ in iter_entries(entry))
            plan.append({"path": nm + "/", "dest": "?", "reason": f"未知目录（含 {n} 个文件），归属需人工判断"})
            continue
        if nm.startswith(".") or nm in KEEP_ROOT or nm.startswith(KEEP_PREFIX):
            continue  # 隐藏文件与根目录配置/说明，保留
        ext = entry.suffix.lower()
        if ext in DOC_EXTS:
            plan.append({"path": nm, "dest": "docs/", "reason": "文档类扩展名"})
        elif ext in CODE_EXTS:
            plan.append({"path": nm, "dest": "code/", "reason": "代码类扩展名"})
        elif ext in TMP_EXTS:
            plan.append({"path": nm, "dest": "tmp/", "reason": "数据/媒体/临时产物"})
        else:
            plan.append({"path": nm, "dest": "?", "reason": "无法判断，需人工分类"})
    return plan


def apply_plan(root: Path, plan: list[dict]) -> tuple[list[str], list[str]]:
    """执行迁移建议中无争议的移动（仅 docs/、code/、tmp/ 三类）。"""
    actions: list[str] = []
    problems: list[str] = []
    for item in plan:
        if item["dest"] not in ("docs/", "code/", "tmp/"):
            continue
        src = root / item["path"]
        if not src.is_file():
            continue
        dest_dir = root / item["dest"]
        dest_dir.mkdir(exist_ok=True)
        target = dest_dir / src.name
        if target.exists():
            problems.append(f"目标已存在，跳过: {item['dest']}{src.name}")
            continue
        if (root / ".git").is_dir():
            rc, _ = run_git(root, "mv", str(src), str(target))
            if rc == 0:
                actions.append(f"{src.name} -> {item['dest']}")
                continue
        shutil.move(str(src), str(target))
        actions.append(f"{src.name} -> {item['dest']}")
    return actions, problems


def print_adopt_report(root: Path, plan: list[dict], applied: bool) -> None:
    print("\n=== 接管分析 ===")
    label = {"docs/": "建议 docs/", "code/": "建议 code/", "tmp/": "建议 tmp/", "?": "需人工判断"}
    n = 0
    for key in ("docs/", "code/", "tmp/", "?"):
        for it in plan:
            if it["dest"] == key:
                print(f"  {label[key]:10s} {it['path']:42s} {it['reason']}")
                n += 1
    if n == 0:
        print("  未发现需要迁移的散落文件")
    if applied:
        actions, problems = apply_plan(root, plan)
        print(f"\n=== 已移动 {len(actions)} 项 ===")
        for a in actions:
            print("  " + a)
        for p in problems:
            print("  [跳过] " + p)
        print("提醒: 为移入 docs/、code/ 的文件补建同名 .log.md（可用 check_project.py --fix），随后 git commit。")
    else:
        print("\n以上仅为建议，未移动任何文件。确认后加 --apply 执行（仅移动 docs/、code/、tmp/ 三类，「需人工判断」项不动）。")


def do_upgrade(root: Path) -> int:
    agents = root / "AGENTS.md"
    if not agents.exists():
        print(f"[升级] {root} 下没有 AGENTS.md，无规范可升级（如需初始化请去掉 --upgrade）")
        return 1
    cur = agents.read_text(encoding="utf-8", errors="replace")

    def field(pat: str, default: str) -> str:
        m = re.search(pat, cur, re.M)
        v = m.group(1).strip() if m else ""
        return v if v and not v.startswith("（") else default

    name = field(r"^-\s*项目名称[：:]\s*(.+)$", root.name)
    stack = field(r"^-\s*技术栈[：:]\s*(.+)$", "（未填写；可编辑本行或用 --stack 指定）")
    mver = re.search(r"规范版本[：:]\s*(\S+)", cur)
    curver = mver.group(1) if mver else "未知"

    new = render_template(name, stack)
    if cur == new:
        print(f"[升级] 已是最新规范版本 {VERSION}，无需操作")
        return 0

    diff = list(difflib.unified_diff(cur.splitlines(), new.splitlines(),
                                     fromfile=f"AGENTS.md（当前 {curver}）",
                                     tofile=f"AGENTS.md（新模板 {VERSION}）", lineterm=""))
    print("\n".join(diff[:200]))
    if len(diff) > 200:
        print(f"…（diff 共 {len(diff)} 行，已截断，完整新模板见 tmp/AGENTS.new.md）")
    out = root / "tmp" / "AGENTS.new.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(new, encoding="utf-8", newline="\n")
    print(f"\n[升级] 当前版本 {curver} → 新模板 {VERSION}")
    print(f"[升级] 新模板已写入 {out.relative_to(root).as_posix()}；请逐段核对后手动合并到 AGENTS.md（规范文件修改须经所有者确认），合并后删除该临时文件并提交。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="项目初始化/接管/升级：git + 规范目录 + 多 agent 规范文件")
    ap.add_argument("target", nargs="?", default=".", help="目标项目目录，默认当前目录")
    ap.add_argument("--name", help="项目名，默认取目录名")
    ap.add_argument("--stack", help="技术栈描述，写入 AGENTS.md")
    ap.add_argument("--for", dest="agents", default="all",
                    help="all | minimal | claude,gemini,qwen,cursor,windsurf,cline,copilot")
    ap.add_argument("--adopt", action="store_true", help="接管已有项目：补规范结构并输出迁移建议")
    ap.add_argument("--apply", action="store_true", help="与 --adopt 连用：执行无争议的文件移动")
    ap.add_argument("--upgrade", action="store_true", help="比对规范模板版本，生成更新 diff 与新模板")
    ap.add_argument("--no-software", action="store_true",
                    help="不生成程序项目脚手架（PRD/Design/TDD/开发进度 及 features/）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的规范文件")
    ap.add_argument("--no-git", action="store_true", help="跳过 git 初始化")
    args = ap.parse_args()

    root = Path(args.target).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.upgrade:
        return do_upgrade(root)

    had_preexisting = any(root.iterdir())
    project_name = args.name or root.name
    stack = args.stack or "（未填写；可编辑本行或用 --stack 指定）"
    created: list[str] = []
    skipped: list[str] = []

    def write(rel: str, content: str, label: str) -> None:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if f.exists() and not args.force:
            skipped.append(label)
            return
        f.write_text(content, encoding="utf-8", newline="\n")
        created.append(label)

    # 1) git init
    new_repo = False
    if args.no_git:
        print("[git] 按参数跳过 init")
    elif (root / ".git").exists():
        print("[git] 已是 git 仓库，跳过 init")
    else:
        rc, out = run_git(root, "init", "-b", "main")
        if rc != 0:
            rc, out = run_git(root, "init")
        print(f"[git] init: {out.splitlines()[0] if out else 'done'}")
        new_repo = True

    # 2) 规范目录
    for d in ("docs", "code", "tmp"):
        (root / d).mkdir(exist_ok=True)
    (root / "docs" / "assets").mkdir(exist_ok=True)
    write("docs/.gitkeep", "", "docs/")
    write("code/.gitkeep", "", "code/")
    write("docs/assets/.gitkeep", "", "docs/assets/")
    print("[目录] docs/ code/ tmp/ docs/assets/ 就绪")

    # 3) .gitignore
    write(".gitignore", GITIGNORE, ".gitignore")

    # 4) AGENTS.md（唯一规范来源）
    write("AGENTS.md", render_template(project_name, stack), "AGENTS.md")

    # 5) 各 agent 入口
    sel = args.agents.strip().lower()
    if sel == "minimal":
        chosen: list[str] = []
    elif sel == "all":
        chosen = list(ADAPTERS)
    else:
        req = [a.strip() for a in sel.split(",") if a.strip()]
        chosen = [a for a in req if a in ADAPTERS]
        unknown = [a for a in req if a not in ADAPTERS]
        if unknown:
            print(f"[警告] 未知的 agent: {', '.join(unknown)}（可选: {', '.join(ADAPTERS)}）")
    for a in chosen:
        write(ADAPTERS[a]["path"], ADAPTERS[a]["body"], a)

    # 5.5) 程序项目脚手架：四份顶层文档（各配 .log.md）+ 功能文档目录
    if args.no_software:
        print("[软件] 按参数跳过程序项目脚手架")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for name in ("PRD.md", "Design.md", "TDD.md", "开发进度.md"):
            tpl = SOFTWARE_TPL_DIR / name
            content = tpl.read_text(encoding="utf-8") if tpl.exists() else f"# {name}\n\n（模板缺失，请补全 skill 的 assets/software/{name}）\n"
            write(f"docs/{name}", content, f"docs/{name}")
            stem = Path(name).stem
            write(f"docs/{stem}.log.md",
                  f"## {now} — 创建\n- 修改者：project-init 脚本\n- 摘要：初始化脚手架\n- 原因：项目初始化\n",
                  f"docs/{stem}.log.md")
        (root / "docs" / "features").mkdir(exist_ok=True)
        write("docs/features/.gitkeep", "", "docs/features/")
        print("[软件] docs/ 顶层文档（PRD/Design/TDD/开发进度）与 features/ 就绪")

    # 6) README
    write("README.md", README_TPL.format(name=project_name), "README.md")

    # 7) 接管分析（不自动提交用户已有文件）
    if args.adopt:
        print_adopt_report(root, adopt_plan(root), args.apply)
        return 0

    # 8) 新仓库首次提交（git 身份未配置则跳过；接管有存量文件的项目时不自动提交）
    if new_repo:
        _, name = run_git(root, "config", "user.name")
        _, mail = run_git(root, "config", "user.email")
        if not (name.strip() and mail.strip()):
            print("[git] 未配置 user.name/email，跳过首次提交（配置后手动 git add -A && git commit）")
        elif args.adopt and had_preexisting:
            print("[git] 接管模式且有存量文件，跳过自动首提（迁移完成后一并提交）")
        else:
            run_git(root, "add", "-A")
            rc, out = run_git(root, "commit", "-m", "chore: 项目初始化（git + 规范目录 + agent 规范文件）")
            print(f"[git] 首次提交: {'完成' if rc == 0 else '失败：' + out.splitlines()[0]}")

    # 9) 汇总
    print("\n=== 初始化完成 ===")
    print(f"项目: {project_name}    规范版本: {VERSION}    目录: {root}")
    if created:
        print("已创建: " + ", ".join(created))
    if skipped:
        print("已存在而跳过（--force 可覆盖）: " + ", ".join(skipped))
    print("提示: 本会话后续工作请遵守项目内 AGENTS.md；可用 check_project.py 做规范巡检。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
