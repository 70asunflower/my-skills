#!/usr/bin/env python3
"""把本机 ZCode 用户技能同步进本仓库。

用法：
    python scripts/sync_zcode_skills.py           # 同步清单内的技能并打印变更
    python scripts/sync_zcode_skills.py --list    # 只看清单与差异，不写文件

口径说明：
- SYNC_SKILLS 维护"哪些技能属于本仓库"——新增自制技能后把目录名加进清单再跑一次。
- 本仓库是公开仓库，第三方技能（Wind/Kimi 官方、Academic pack、FBSir 等）一律不入库。
- 同步后跑 `python scripts/check_consistency.py`，并记得把新技能补进 README 表格。

同步后置流程（本仓库约定）：
    1. python scripts/sync_zcode_skills.py
    2. 编辑 README.md 补技能行（CI 双向校验强制）
    3. python scripts/check_consistency.py && git commit && git push
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

SRC_ROOT = Path.home() / ".zcode" / "skills"
REPO_ROOT = Path(__file__).resolve().parent.parent

# 自制技能清单（公开仓库，第三方一律不收）
SYNC_SKILLS = [
    # —— WorkBuddy 时代自制，迁移自 ~/.workbuddy/skills ——
    "ai-tutorial-pipeline",
    "doc-plain-zh",
    "jetson-thor-mem-diag",
    "siyuan-backup-sync",
    "siyuan-kernel-ops",
    "siyuan-markdown-formula-formatter",
    "strict-docx-audit",
    "trek-mcp-ops",
    # —— ZCode 时代自制 ——
    "investment-analysis",
    "paper-figures",
    "project-init",
    "project-review",
    "snap",
    "svg-diagram-pipeline",
    "xhs-pipeline",
]


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not any(
            part in (".git", "__pycache__", "node_modules") for part in p.parts
        ):
            yield p


def diff_count(src: Path, dst: Path) -> tuple[int, int]:
    """返回 (新增, 更新)；更新 = 两边都有但内容不同。"""
    new = updated = 0
    for sf in iter_files(src):
        rel = sf.relative_to(src)
        df = dst / rel
        if not df.exists():
            new += 1
        elif not filecmp.cmp(sf, df, shallow=False):
            updated += 1
    return new, updated


def junction_into_repo(name: str) -> bool:
    """该技能目录是否已被 skillsync 接管（junction 指向本仓库）。"""
    src = SRC_ROOT / name
    try:
        if not src.exists() or not os.path.isjunction(src):
            return False
        target = Path(os.readlink(src)).resolve()
        repo = REPO_ROOT.resolve()
        return target == repo or repo in target.parents
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="只打印差异，不落盘")
    args = ap.parse_args()

    # 安全闸（硬）: 本脚本的语义是「从 agent 目录单向复制进仓库」，会先 rmtree 仓库目录。
    # skillsync 接管后，agent 目录对该技能是 junction 指向仓库，源与目标是同一份文件；
    # 即使不是 junction（冲突技能），复制方向也与新架构相反，会把仓库内容覆盖掉。
    # 因此只要本机存在 skillsync 配置，一律拒绝执行。
    if (Path.home() / ".agents" / "skillsync.json").exists() or any(
        junction_into_repo(n) for n in SYNC_SKILLS
    ):
        print("已废弃：本仓库的 agent 技能目录已由 skillsync 统一管理。\n")
        print("本脚本会「先删除仓库目录、再从 agent 目录复制」，在新布局下方向相反，")
        print("继续运行可能覆盖仓库内容，因此拒绝执行。\n")
        print("改用 skillsync：")
        print("  python ~/.agents/skillsync.py status   # 各 agent 技能状态")
        print("  python ~/.agents/skillsync.py doctor   # 结构问题检查")
        print("  python ~/.agents/skillsync.py scan     # 副本漂移报告")
        print("\n改动直接在本仓库编辑即可，各 agent 通过 junction 自动同步，无需再手动同步。")
        return 2

    if not SRC_ROOT.is_dir():
        print(f"找不到技能源目录：{SRC_ROOT}")
        return 1

    rc = 0
    for name in SYNC_SKILLS:
        src = SRC_ROOT / name
        dst = REPO_ROOT / name
        if not src.is_dir():
            print(f"[缺失] {name}: 本机 {src} 不存在")
            rc = 1
            continue
        new, updated = diff_count(src, dst)
        gone = (
            len([f for f in iter_files(dst) if not (src / f.relative_to(dst)).exists()])
            if dst.is_dir()
            else 0
        )
        tag = "无变化" if not (new or updated or gone) else f"+{new} 新增 ~{updated} 更新 -{gone} 冗余"
        print(f"[{tag}] {name}")
        if args.list or (not new and not updated and not gone):
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))

    if not args.list:
        print("\n完成。下一步：更新 README 表格 → python scripts/check_consistency.py → commit & push")
    return rc


if __name__ == "__main__":
    sys.exit(main())
