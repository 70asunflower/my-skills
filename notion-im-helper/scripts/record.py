"""Unified record entry — dispatch by type to create Notion blocks."""
import os
import sys
import json
import argparse

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

# Core (generic, portable)
from core.blocks import (
    build_paragraph, build_callout, build_divider,
    build_heading, build_quote_block, build_bullet, build_numbered, build_toggle,
    TYPE_CONFIG,
)
from core.dispatch import (
    check_need_day_separator, build_blocks_for_type, parse_format_line,
    set_api_funcs,
)

# Client (connects to user-specific Notion config)
from notion_client import (
    api_request, append_blocks, append_to_block,
    get_children as _get_children_fn,
    get_last_callout_block, delete_last_block,
    upload_file as _upload_file_fn,
    set_active_page,
)

# Wire up API funcs for dispatch module
set_api_funcs(_upload_file_fn, _get_children_fn)


PENDING_CONTENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pending_content.txt")
PENDING_IMAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pending_image.jpg")


# ---- Command handlers ----

def cmd_record(args):
    set_active_page(args.page)
    cfg = TYPE_CONFIG.get(args.type, TYPE_CONFIG["idea"])
    if args.file_path:
        with open(args.file_path, "r", encoding="utf-8") as f:
            full_content = f.read().strip()
    elif args.stdin_content:
        full_content = sys.stdin.read().strip()
    elif args.content:
        full_content = " ".join(args.content)
    elif os.path.exists(PENDING_CONTENT_FILE):
        with open(PENDING_CONTENT_FILE, "r", encoding="utf-8") as f:
            full_content = f.read().strip()
        os.remove(PENDING_CONTENT_FILE)
    else:
        full_content = ""
    blocks = []

    if check_need_day_separator():
        blocks.append(build_divider())

    callout_types = {"idea", "diary", "note", "question", "quote"}

    if args.type in callout_types:
        blocks.extend(build_blocks_for_type(args.type, full_content))
    else:
        lines = full_content.split("\n")
        content_lines = []
        for line in lines:
            fmt_block = parse_format_line(line)
            if fmt_block is not None:
                if content_lines:
                    content_text = "\n".join(content_lines)
                    blocks.extend(build_blocks_for_type(args.type, content_text))
                    content_lines = []
                blocks.append(fmt_block)
            else:
                content_lines.append(line)

        if content_lines:
            blocks.extend(build_blocks_for_type(args.type, "\n".join(content_lines)))

    if not blocks:
        print("OK|没有内容可记录")
        return

    append_blocks(blocks, silent=True)
    type_label = cfg["label"]
    if args.type in ("todo", "done"):
        count = len([b for b in blocks if b.get("type") == "to_do"])
        print(f"OK|已记录到 Notion，共 {count} 条{type_label}")
    else:
        print(f"OK|已记录到 Notion，共 {len(blocks)} 条 ✅")


def cmd_heading(args):
    set_active_page(args.page)
    blocks = [build_heading(args.level, " ".join(args.content))]
    append_blocks(blocks, silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_divider(args):
    set_active_page(args.page)
    append_blocks([build_divider()], silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_list(args):
    set_active_page(args.page)
    builder = build_bullet if args.kind == "bullet" else build_numbered
    blocks = [builder(text) for text in args.content]
    append_blocks(blocks, silent=True)
    print("OK|已记录到 Notion ✅")


def cmd_toggle(args):
    set_active_page(args.page)
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


def cmd_image(args):
    """Upload an image and append to Notion page."""
    set_active_page(args.page)
    path = " ".join(args.path)
    blocks = []

    if check_need_day_separator():
        blocks.append(build_divider())

    # Build image block using build_blocks_for_type which handles upload
    image_blocks = build_blocks_for_type("image", path)
    blocks.extend(image_blocks)

    if blocks:
        append_blocks(blocks, silent=True)
        print("OK|已记录图片到 Notion ✅")


def cmd_caption(args):
    """Append caption content as gray paragraphs inside the last callout block."""
    set_active_page(args.page)
    if args.file_path:
        with open(args.file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    elif args.stdin_content:
        content = sys.stdin.read().strip()
    elif args.content:
        content = " ".join(args.content).strip()
    elif os.path.exists(PENDING_CONTENT_FILE):
        with open(PENDING_CONTENT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        os.remove(PENDING_CONTENT_FILE)
    else:
        content = ""

    if not content:
        print("OK|没有内容可追加")
        return

    last_callout = get_last_callout_block()
    if not last_callout:
        print("ERROR| Notion 页面上没有记录，无法追加")
        return

    block_id = last_callout["id"]
    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
    children = [build_paragraph(p, color="gray") for p in paragraphs]

    append_to_block(block_id, children, silent=True)
    print("OK|已追加到上一条记录 ✅")


def cmd_undo(args):
    set_active_page(args.page)
    delete_last_block()


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(description="Unified Notion record entry")
    sub = parser.add_subparsers(dest="command")

    # record command
    p = sub.add_parser("record")
    p.add_argument("--type", required=True)
    p.add_argument("--page", default=None, help="Target page name from pages.json (e.g., 'lifeos')")
    p.add_argument("--stdin-content", action="store_true", dest="stdin_content",
                   help="Read content from stdin instead of args (avoids shell variable expansion)")
    p.add_argument("--file", dest="file_path", default=None,
                   help="Read content from file (avoids shell encoding issues)")
    p.add_argument("content", nargs="*")
    p.set_defaults(func=cmd_record)

    # heading command
    p = sub.add_parser("heading")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
    p.add_argument("--level", type=int, default=2)
    p.add_argument("content", nargs="+")
    p.set_defaults(func=cmd_heading)

    # divider command
    p = sub.add_parser("divider")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
    p.set_defaults(func=cmd_divider)

    # list command
    p = sub.add_parser("list")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
    p.add_argument("--kind", choices=["bullet", "number"], default="bullet")
    p.add_argument("content", nargs="+")
    p.set_defaults(func=cmd_list)

    # toggle command
    p = sub.add_parser("toggle")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
    p.add_argument("content", nargs="*")
    p.set_defaults(func=cmd_toggle)

    # image command
    p = sub.add_parser("image")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
    p.add_argument("--caption", default=None, help="Optional caption for the image")
    p.add_argument("path", nargs="+", help="Local file path or URL of the image")
    p.set_defaults(func=cmd_image)

    # caption command — append to last callout
    p = sub.add_parser("caption")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
    p.add_argument("--stdin-content", action="store_true", dest="stdin_content",
                   help="Read content from stdin")
    p.add_argument("--file", dest="file_path", default=None,
                   help="Read content from file")
    p.add_argument("content", nargs="*", help="Content to append")
    p.set_defaults(func=cmd_caption)

    # undo command
    p = sub.add_parser("undo")
    p.add_argument("--page", default=None, help="Target page name from pages.json")
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
