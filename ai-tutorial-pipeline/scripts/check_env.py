# -*- coding: utf-8 -*-
"""环境自检：WebBridge 守护进程/扩展、思源内核、目标父文档解析。输出 JSON。
用法: python check_env.py [--parent <文档ID或标题关键词>] [--chat <url>]
"""
import argparse, json, os, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import siyuan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", help="父文档 ID 或标题关键词")
    ap.add_argument("--chat", default="https://chat.qwen.ai/")
    args = ap.parse_args()

    out = {"bridge": "down", "kernel": None, "parent": None, "candidates": [], "chat": args.chat}

    try:
        wb.ensure_daemon(wait_ext=30)
        out["bridge"] = "ok"
    except Exception as e:
        out["bridge_error"] = str(e)

    try:
        base, token = siyuan.connect()
        out["kernel"] = base
        if args.parent:
            hint = args.parent
            if len(hint) == 22 and "-" in hint:  # 思源块 ID 形如 20260829193220-i8sda14
                try:
                    info = siyuan.doc_info(base, token, hint)
                    out["parent"] = {"id": hint, "notebook": info["notebook"], "hpath": info["hpath"]}
                except Exception as e:
                    out["parent_error"] = str(e)
            if not out["parent"]:
                found = siyuan.search_docs(base, token, hint, limit=5)
                exact = [d for d in found if d["title"] == hint]
                pick = exact or found
                if pick:
                    d = pick[0]
                    info = siyuan.doc_info(base, token, d["id"])
                    out["parent"] = {"id": d["id"], "notebook": info["notebook"], "hpath": info["hpath"]}
                out["candidates"] = found
        else:
            out["candidates"] = siyuan.recent_docs(base, token, limit=12)
    except Exception as e:
        out["kernel_error"] = str(e)

    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
