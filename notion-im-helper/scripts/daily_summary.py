"""Daily summary, weekly report, and random quote extraction."""
import os
import sys
import random
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
from notion_client import get_children, PAGE_ID


def extract_text(block):
    """Extract text content from a block."""
    block_type = block.get("type", "")
    content = block.get(block_type, {})
    rich = content.get("rich_text", [])
    text = ""
    for item in rich:
        text += item.get("text", {}).get("content", "")
    return text.strip()


def get_today_blocks():
    """Get all blocks from the page (recent ones, last N blocks)."""
    result = get_children(page_size=100)
    if not result or "results" not in result:
        return []
    return result["results"]


def generate_daily_summary():
    """Generate a daily summary from recent blocks."""
    blocks = get_today_blocks()
    if blocks is None or not blocks:
        return "📊 今日简报\n\n今天还没有记录呢，去记点什么吧~"

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"📊 今日简报（{today}）\n"]

    type_counts = {}
    items = []

    for block in blocks:
        block_type = block.get("type", "")
        text = extract_text(block)
        if not text:
            continue

        # Determine type from content
        if "📅" in text:
            t = "日记"
        elif "💡" in text or "想法" in text:
            t = "想法"
        elif "📝" in text:
            t = "笔记"
        elif "📖" in text or "摘抄" in text:
            t = "摘抄"
        elif "❓" in text:
            t = "问题"
        elif block_type == "to_do":
            checked = block.get("to_do", {}).get("checked", False)
            t = "已完成" if checked else "待办"
        elif block_type == "bookmark":
            t = "链接"
        elif block_type in ("divider", "heading_1", "heading_2", "heading_3"):
            continue
        elif block_type in ("bulleted_list_item", "numbered_list_item"):
            continue
        else:
            t = "其他"

        type_counts[t] = type_counts.get(t, 0) + 1
        if text and len(text) < 100:
            items.append((t, text.replace("\n", " ")))

    lines.append(f"共 {sum(type_counts.values())} 条记录：")
    for t, c in type_counts.items():
        lines.append(f"  {t}: {c} 条")

    lines.append(f"\n---\n最新记录：")
    for t, text in items[-5:]:
        lines.append(f"  [{t}] {text[:50]}")

    return "\n".join(lines)


def generate_random_quote(count=1):
    """Randomly select historical entries."""
    blocks = get_today_blocks()
    if not blocks:
        return "📖 还没有摘抄呢，先去记点什么吧~"

    # Filter out structural blocks
    candidates = []
    for block in blocks:
        text = extract_text(block)
        if text and ("📖" in text or "📝" in text or "💡" in text or "📅" in text):
            clean = text.replace("\n", " ").strip()
            if clean:
                candidates.append(clean)

    if not candidates:
        return "📖 没有找到合适的摘抄内容~"

    selected = random.sample(candidates, min(count, len(candidates)))
    lines = ["📖 随机回忆~"]
    for i, text in enumerate(selected, 1):
        lines.append(f"{i}. {text[:80]}")
    return "\n".join(lines)


def generate_weekly_report():
    """Simple weekly summary."""
    blocks = get_today_blocks()
    if blocks is None:
        return "📊 本周简报\n\n暂时无法获取记录，请稍后重试。"
    total = len([b for b in blocks if extract_text(b)])
    return f"📊 本周简报\n\n本周尚无自动周统计能力，累计记录约 {total} 条。\n建议：保持每日 3+ 条记录！"


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "daily"

    if command in ("daily", "日报"):
        result = generate_daily_summary()
    elif command in ("quote", "random", "随机摘抄", "摘抄"):
        count = 1
        if len(sys.argv) > 2:
            try:
                count = int(sys.argv[2])
            except ValueError:
                pass
        result = generate_random_quote(count)
    elif command in ("weekly", "周报"):
        result = generate_weekly_report()
    else:
        result = generate_daily_summary()

    print(f"OK|{result}")


if __name__ == "__main__":
    main()
