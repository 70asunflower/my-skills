"""Unified record entry - dispatch by type to create Notion blocks."""
import os
import re
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
from notion_client import api_request, append_blocks, PAGE_ID, get_children, delete_last_block


# ---- Block builders ----

def build_callout(emoji, text, color="default"):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": color,
        },
    }


def build_todo(text, checked=False):
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "checked": checked,
            "color": "default",
        },
    }


def build_bookmark(url):
    return {
        "object": "block",
        "type": "bookmark",
        "bookmark": {"url": url, "rich_text": [{"type": "text", "text": {"content": url}}]},
    }


def build_heading(level, text):
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": "default",
        },
    }


def build_quote_block(text):
    return {
        "object": "block",
        "type": "quote",
        "quote": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": "default"},
    }


def build_divider():
    return {"object": "block", "type": "divider", "divider": {}}


def build_bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": "default"},
    }


def build_numbered(text):
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": "default"},
    }


def build_toggle(text, children=None):
    block = {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "color": "default",
        },
    }
    if children:
        block["toggle"]["children"] = children
    return block


# ---- Type configs ----

TYPE_CONFIG = {
    "idea": {"emoji": "💡", "color": "default", "label": "想法"},
    "diary": {"emoji": "📒", "color": "blue", "label": "日记"},
    "todo": {"emoji": "☐", "color": "default", "label": "待办"},
    "done": {"emoji": "✔️", "color": "default", "label": "已完成"},
    "note": {"emoji": "📝", "color": "yellow", "label": "笔记"},
    "question": {"emoji": "❓", "color": "purple", "label": "问题"},
    "quote": {"emoji": "📖", "color": "green", "label": "摘抄"},
    "link": {"emoji": "🔗", "color": "default", "label": "链接"},
}


def parse_metadata(text):
    """Extract tags (#xxx) and project (/p:xxx) from end of text."""
    tags = []
    project = None

    # Scan from the end of text, line by line
    lines = text.strip().split("\n")
    meta_line_indices = []
    remaining_lines = []

    for i, line in enumerate(lines):
        tokens = line.split()
        is_meta_line = False
        for tok in tokens:
            if tok.startswith("#") or tok.startswith("/p:"):
                is_meta_line = True
                break
        if is_meta_line:
            meta_line_indices.append(i)
        else:
            remaining_lines.append(line)

    # Extract tags and project from meta lines
    meta_text = " ".join(lines[i] for i in meta_line_indices)
    for tok in meta_text.split():
        if tok.startswith("#"):
            tags.append(tok[1:])
        elif tok.startswith("/p:"):
            project = tok[3:]

    clean_text = "\n".join(remaining_lines).strip()
    return clean_text, tags, project


def extract_date_from_block(block):
    """Try to extract YYYY-MM-DD from block text content."""
    block_type = block.get("type", "")
    content = block.get(block_type, {})
    rich = content.get("rich_text", [])
    text = ""
    for item in rich:
        text += item.get("text", {}).get("content", "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def check_need_day_separator():
    """Check if the last block on the page is from a different day."""
    data = get_children(page_size=5, silent=True)
    if not data or "results" not in data:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    for block in reversed(data["results"]):
        block_date = extract_date_from_block(block)
        if block_date:
            return block_date != today
    return False


def build_blocks_for_type(record_type, content):
    """Build Notion blocks for a given type and content."""
    cfg = TYPE_CONFIG.get(record_type, TYPE_CONFIG["idea"])

    if record_type == "todo":
        items = []
        for sep in [", ", ",", "，", "、"]:
            if sep in content:
                items = [x.strip() for x in content.split(sep) if x.strip()]
                break
        if not items:
            items = [content]
        return [build_todo(item, checked=False) for item in items]

    if record_type == "done":
        items = []
        for sep in [", ", ",", "，", "、"]:
            if sep in content:
                items = [x.strip() for x in content.split(sep) if x.strip()]
                break
        if not items:
            items = [content]
        return [build_todo(item, checked=True) for item in items]

    if record_type == "link":
        url = content.strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return [build_bookmark(url)]

    if record_type in ("idea", "diary", "note", "question", "quote"):
        clean_text, tags, project = parse_metadata(content)

        # Header line: YYYY-MM-DD HH:mm (emoji is from callout icon, don't duplicate)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        header = now_str

        # Build content lines
        body_parts = [header, clean_text]

        meta_parts_list = []
        if tags:
            meta_parts_list.append(f"#标签：{' '.join('#' + t for t in tags)}")
        if project:
            meta_parts_list.append(f"/项目：{project}")

        if meta_parts_list:
            body_parts.append(" | ".join(meta_parts_list))

        full_text = "\n".join(body_parts)
        return [build_callout(cfg["emoji"], full_text, cfg["color"])]

    return []


# ---- Main dispatch ----

def cmd_record(args):
    cfg = TYPE_CONFIG.get(args.type, TYPE_CONFIG["idea"])
    blocks = []

    # Check if we need a day separator
    if check_need_day_separator():
        blocks.append(build_divider())

    blocks.extend(build_blocks_for_type(args.type, " ".join(args.content)))

    if not blocks:
        print("OK|没有内容可记录")
        return

    append_blocks(blocks, silent=True)
    type_label = cfg["label"]
    if args.type in ("todo", "done"):
        count = len([b for b in blocks if b.get("type") == "to_do"])
        print(f"OK|已记录到 Notion，共 {count} 条{type_label}")
    else:
        print("OK|已记录到 Notion ✅")


def cmd_heading(args):
    blocks = [build_heading(args.level, " ".join(args.content))]
    append_blocks(blocks, silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_divider(_args):
    append_blocks([build_divider()], silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_list(args):
    builder = build_bullet if args.kind == "bullet" else build_numbered
    blocks = [builder(text) for text in args.content]
    append_blocks(blocks, silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_toggle(args):
    # JSON input from stdin or args
    if args.content:
        data = json.loads(" ".join(args.content))
    else:
        try:
            data = json.loads(sys.stdin.read())
        except Exception:
            print("ERROR| 无效的 toggle 数据")
            return
    blocks = [build_toggle(data["title"], data.get("children"))]
    append_blocks(blocks, silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_undo(_args):
    delete_last_block()


def main():
    parser = argparse.ArgumentParser(description="Unified Notion record entry")
    sub = parser.add_subparsers(dest="command")

    # record command
    p = sub.add_parser("record")
    p.add_argument("--type", required=True)
    p.add_argument("content", nargs="+")
    p.set_defaults(func=cmd_record)

    # heading command
    p = sub.add_parser("heading")
    p.add_argument("--level", type=int, default=2)
    p.add_argument("content", nargs="+")
    p.set_defaults(func=cmd_heading)

    # divider command
    p = sub.add_parser("divider")
    p.set_defaults(func=cmd_divider)

    # list command
    p = sub.add_parser("list")
    p.add_argument("--kind", choices=["bullet", "number"], default="bullet")
    p.add_argument("content", nargs="+")
    p.set_defaults(func=cmd_list)

    # toggle command
    p = sub.add_parser("toggle")
    p.add_argument("content", nargs="*")
    p.set_defaults(func=cmd_toggle)

    # undo command
    p = sub.add_parser("undo")
    p.set_defaults(func=cmd_undo)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    try:
        args.func(args)
    except Exception as e:
        print(f"ERROR| 操作失败: {e}")


if __name__ == "__main__":
    main()
