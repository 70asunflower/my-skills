"""Unified OS record entry — dispatch parsed os commands to lifeos operations.

Usage:
    python scripts/os_entry.py "os l 晨跑 @身体 energy:h duration:30"
    python scripts/os_entry.py "os i 试试Obsidian @学习 source:ai"
    python scripts/os_entry.py "os h 冥想"
    python scripts/os_entry.py "os 今天"
"""
import os
import sys
import argparse

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from os_parser import parse
from user.lifeos.commands import (
    cmd_log, cmd_idea, cmd_habit_check, cmd_habit_streaks,
    cmd_log_today, cmd_log_history, cmd_ideas_list,
)


def dispatch(parsed):
    """Route parsed command to the correct lifeos operation.

    Args:
        parsed: Dict from os_parser.parse()

    Returns:
        True on success, False on error.
    """
    if parsed.get("error"):
        print(f"ERROR| {parsed['error']}")
        return False

    command = parsed["command"]
    content = parsed.get("content")
    bucket = parsed.get("bucket")       # English short name
    energy_raw = parsed.get("energy")   # "high"/"medium"/"low"
    duration = parsed.get("duration")
    source = parsed.get("source")
    urgency = parsed.get("urgency")     # "Now"/"ThisWeek"/"Later"
    notes = parsed.get("notes")
    mood = parsed.get("mood")

    try:
        # ---- Write commands ----

        if command == "log":
            # Convert energy from "high"/"medium"/"low" to "h"/"m"/"l" for cmd_log
            energy_short = None
            if energy_raw:
                energy_map = {"high": "h", "medium": "m", "low": "l"}
                energy_short = energy_map.get(energy_raw, energy_raw)
            cmd_log(content, bucket_name=bucket, energy=energy_short,
                    duration=duration, notes=notes, mood=mood)
            return True

        elif command == "idea":
            cmd_idea(content, bucket_name=bucket, source=source, urgency=urgency or "Later")
            return True

        elif command == "habit":
            cmd_habit_check(content)
            return True

        elif command == "streaks":
            cmd_habit_streaks()
            return True

        # ---- Read commands ----

        elif command == "today":
            cmd_log_today()
            return True

        elif command == "week":
            cmd_log_history(days=7, bucket_name=bucket)
            return True

        elif command == "bucket":
            # Show recent entries for a specific bucket
            if not bucket:
                print("ERROR| 请指定桶名，例如: os 桶 @身体")
                return False
            cmd_log_history(days=14, bucket_name=bucket)
            return True

        elif command == "ideas_list":
            cmd_ideas_list()
            return True

        # ---- Review commands (simple summary for now) ----

        elif command in ("weekly", "monthly"):
            print(f"INFO| {command} review generation coming soon. Use `os {command}` to trigger agent analysis.")
            return True

        elif command == "adventure":
            print("INFO| Adventure listing coming soon.")
            return True

        else:
            print(f"ERROR| 未知命令: {command}")
            return False

    except Exception as e:
        print(f"ERROR| 操作失败: {e}")
        return False


# ---- CLI entry ----

def main():
    parser = argparse.ArgumentParser(description="8+1 Life OS sync entry")
    parser.add_argument(
        "message", nargs="*",
        help="os command message, e.g. 'os l 晨跑 @身体 energy:h duration:30'"
    )
    parser.add_argument(
        "--stdin", action="store_true", dest="from_stdin",
        help="Read message from stdin"
    )

    args = parser.parse_args()

    if args.from_stdin:
        message = sys.stdin.read().strip()
    elif args.message:
        message = " ".join(args.message)
    else:
        parser.print_help()
        return

    if not message.strip():
        print("ERROR| 请提供 os 命令")
        return

    parsed = parse(message)
    dispatch(parsed)


if __name__ == "__main__":
    main()
