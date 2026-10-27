"""提交前闸门：一致性 + 结构回归。

装到 .git/hooks/pre-commit 后，每次提交前自动运行（见 scripts/git-hooks/pre-commit）。

判定原则：**只拦新增问题，不为历史欠账买单**。
- check_consistency.py 失败 → 拒绝提交（README 与目录必须双向一致）
- doctor 报出**新的**链式 junction → 拒绝提交（旧的记在 baseline 里，已豁免）
- 真实副本数上涨 → 只警告（副本归集需要人工判断，不该堵住提交）

修好历史欠账后跑 `python scripts/precommit.py --update-baseline` 刷新豁免清单。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "scripts" / "skillsync-baseline.json"
CHAINED_RE = re.compile(r"^\[链式\]\s+(\S+?)\s")


def run(args):
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def chained_items():
    result = run(["scripts/skillsync.py", "doctor"])
    items = []
    for line in (result.stdout or "").splitlines():
        match = CHAINED_RE.match(line.strip())
        if match:
            items.append(match.group(1))
    return sorted(set(items))


def real_copy_count():
    result = run(["scripts/skillsync.py", "scan"])
    match = re.search(r"真实副本总数\s*(\d+)", result.stdout or "")
    return int(match.group(1)) if match else None


def load_baseline():
    if not BASELINE.is_file():
        return {"chained": [], "intentional": []}
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"chained": [], "intentional": []}
    data.setdefault("chained", [])
    data.setdefault("intentional", [])
    return data


def main():
    if "--update-baseline" in sys.argv:
        previous = load_baseline()
        current = chained_items()
        # intentional 是设计上就不共享的（如第三方技能按渠道各自保留），不随刷新消失
        intentional = [item for item in previous.get("intentional", []) if item in current]
        payload = {
            "intentional": intentional,
            "chained": [item for item in current if item not in intentional],
            "note": "intentional=设计上不共享；chained=待修欠账，目标为空",
        }
        BASELINE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"已更新：intentional {len(payload['intentional'])} 项，"
            f"待修欠账 {len(payload['chained'])} 项"
        )
        return 0

    failures = []

    consistency = run(["scripts/check_consistency.py"])
    if consistency.returncode != 0:
        failures.append(
            "check_consistency.py 未通过（README 与技能目录不一致）\n"
            + (consistency.stdout or "")[-800:]
        )

    current = chained_items()
    baseline = load_baseline()
    allowed = set(baseline["intentional"]) | set(baseline["chained"])
    new_items = [item for item in current if item not in allowed]
    if new_items:
        failures.append(
            "新增链式 junction（必须直接指向主库）：\n  "
            + "\n  ".join(new_items)
            + "\n  修好后跑 python scripts/precommit.py --update-baseline"
        )

    debt = [item for item in current if item in set(baseline["chained"])]
    if debt:
        print(f"[提示] {len(debt)} 项链式欠账待修：{', '.join(debt)}")
    if baseline["intentional"]:
        print(f"[提示] {len(baseline['intentional'])} 项第三方技能按渠道各自保留（设计如此）")

    copies = real_copy_count()
    if copies is not None and copies > 0:
        print(f"[提示] 仍有 {copies} 份真实副本未归集（不阻塞提交，见 skillsync.py scan）")

    if failures:
        print("\n[skillsync] 提交被拒绝\n")
        for item in failures:
            print(item.rstrip() + "\n")
        print("确认无误要跳过：git commit --no-verify")
        return 1

    print("[skillsync] 检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
