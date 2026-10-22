#!/usr/bin/env python3
"""校验仓库一致性，供 CI 与本地提交前使用。

检查项：
1. 每个 skill 目录都含 SKILL.md，且 frontmatter 有 name 字段；
2. frontmatter 的 name 与目录名一致；
3. README 表格列出的 skill 与实际目录双向一致（不多不少）。

退出码 0 表示全部通过，1 表示存在问题。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
GITIGNORE = REPO_ROOT / ".gitignore"
SKIP_DIRS = {"scripts"}
SYNC_BLOCK_BEGIN = "# >>> skillsync"
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\]\(\./([^/]+)/\)")


def third_party_dirs() -> set[str]:
    """skillsync 标记区块里列出的第三方技能目录。

    这些技能由 skillsync 统一管理、以 junction 分发到各 agent，
    但不属于本仓库的内容（版权与权属原因不入库），因此不参与 README 校验。
    """
    if not GITIGNORE.exists():
        return set()
    out: set[str] = set()
    inside = False
    for line in GITIGNORE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(SYNC_BLOCK_BEGIN):
            inside = True
            continue
        if inside and s.startswith("# <<< skillsync"):
            inside = False
            continue
        if inside and s and not s.startswith("#"):
            out.add(s.rstrip("/"))
    return out


def skill_dirs() -> list[str]:
    excluded = third_party_dirs()
    return sorted(
        p.name
        for p in REPO_ROOT.iterdir()
        if p.is_dir()
        and not p.name.startswith((".", "_"))
        and p.name not in SKIP_DIRS
        and p.name not in excluded
    )


def readme_links() -> list[str]:
    if not README.exists():
        return []
    return sorted(set(LINK_RE.findall(README.read_text(encoding="utf-8"))))


def main() -> int:
    errors: list[str] = []
    dirs = skill_dirs()
    links = readme_links()

    for name in dirs:
        skill_file = REPO_ROOT / name / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"{name}: 缺少 SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        match = NAME_RE.search(text)
        if not match:
            errors.append(f"{name}: SKILL.md frontmatter 缺少 name 字段")
        elif match.group(1).strip() != name:
            errors.append(
                f"{name}: frontmatter name 与目录名不一致（{match.group(1).strip()}）"
            )

    missing_in_readme = sorted(set(dirs) - set(links))
    missing_dir = sorted(set(links) - set(dirs))
    for name in missing_in_readme:
        errors.append(f"{name}: 目录存在但 README 未列出")
    for name in missing_dir:
        errors.append(f"{name}: README 已列出但目录不存在")

    if errors:
        print("校验失败：")
        for line in errors:
            print(f"  - {line}")
        return 1

    print(f"校验通过：{len(dirs)} 个 skill，README 与目录一致")
    for name in dirs:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
