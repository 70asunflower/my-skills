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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="只打印差异，不落盘")
    args = ap.parse_args()

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
