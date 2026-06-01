"""Content dispatch logic — generic, no user-specific data."""
import os
import re
from datetime import datetime

from .blocks import (
    build_paragraph, build_callout, build_todo, build_bookmark,
    build_heading, build_quote_block, build_divider,
    build_bullet, build_numbered, build_toggle,
    build_image_block, build_image_block_external,
    TYPE_CONFIG,
)

# Lazy import to avoid circular dependency at module level
_upload_file = None  # set by record.py after import
_get_children = None  # set by record.py after import


def set_api_funcs(upload_file_fn, get_children_fn):
    """Set API functions from notion_client to avoid circular imports."""
    global _upload_file, _get_children
    _upload_file = upload_file_fn
    _get_children = get_children_fn


def parse_metadata(text):
    """Extract tags (#xxx) and project (/p:xxx) from end of text."""
    tags = []
    project = None

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
    if _get_children is None:
        return False
    data = _get_children(page_size=5, silent=True)
    if not data or "results" not in data:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    for block in reversed(data["results"]):
        block_date = extract_date_from_block(block)
        if block_date:
            return block_date != today
    return False


def is_local_file_path(s):
    """Check if string looks like a local file path."""
    if re.match(r'^[A-Za-z]:[/\\]', s):
        return True
    if s.startswith('./') or s.startswith('../') or s.startswith('~'):
        return True
    if os.path.isfile(s):
        return True
    return False


def is_image_url(s):
    """Check if string is an HTTP URL pointing to an image."""
    if not s.startswith("http"):
        return False
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
    return s.lower().split('?')[0].endswith(image_extensions)


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
        url_pattern = r'(https?://[^\s]+)'
        urls = re.findall(url_pattern, content)
        remaining = re.sub(url_pattern, '', content).strip()

        if not urls:
            url = content.strip()
            if not url.startswith("http"):
                url = f"https://{url}"
            return [build_bookmark(url)]

        blocks = []
        for url in urls:
            blocks.append(build_bookmark(url, caption=remaining if remaining else None))
        return blocks

    if record_type == "image":
        path = content.strip()
        if is_image_url(path):
            return [build_image_block_external(path)]
        if is_local_file_path(path):
            path = os.path.expanduser(path)
            if not os.path.isfile(path):
                print(f"ERROR| 文件不存在: {path}")
                return []
            if _upload_file is None:
                print("ERROR| upload_file not configured")
                return []
            file_id = _upload_file(path)
            if not file_id:
                print("ERROR| 图片上传失败")
                return []
            return [build_image_block(file_id)]
        if not path.startswith("http"):
            path = f"https://{path}"
        return [build_image_block_external(path)]

    if record_type in ("idea", "diary", "note", "question", "quote"):
        clean_text, tags, project = parse_metadata(content)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        meta_parts_list = []
        if tags:
            meta_parts_list.append(f"#标签：{' '.join('#' + t for t in tags)}")
        if project:
            meta_parts_list.append(f"/项目：{project}")
        meta_line = " | ".join(meta_parts_list) if meta_parts_list else ""

        lines = clean_text.split("\n")
        paragraphs = [line for line in lines if line.strip()]

        CALLOUT_CHAR_LIMIT = 2000
        total_len = sum(len(p) for p in paragraphs)

        if total_len <= CALLOUT_CHAR_LIMIT:
            children = [build_paragraph(p) for p in paragraphs]
            if meta_line:
                children.append(build_paragraph(meta_line))
            return [build_callout(cfg["emoji"], now_str, cfg["color"], children=children)]
        else:
            callout_blocks = []
            current_paras = []
            current_len = 0

            for p in paragraphs:
                if current_len + len(p) > CALLOUT_CHAR_LIMIT and current_paras:
                    children = [build_paragraph(cp) for cp in current_paras]
                    callout_blocks.append(
                        build_callout(cfg["emoji"], now_str, cfg["color"], children=children)
                    )
                    current_paras = []
                    current_len = 0

                current_paras.append(p)
                current_len += len(p)

            if current_paras:
                children = [build_paragraph(cp) for cp in current_paras]
                if meta_line:
                    children.append(build_paragraph(meta_line))
                callout_blocks.append(
                    build_callout(cfg["emoji"], now_str, cfg["color"], children=children)
                )

            if meta_line and not callout_blocks:
                callout_blocks.append(
                    build_callout(cfg["emoji"], now_str,
                                  children=[build_paragraph(meta_line)])
                )

            return callout_blocks

    return []


def parse_format_line(line):
    """Check if a line is a format pattern, return block or None."""
    if line.startswith("* ") and not line.startswith("** ") and not line.startswith("*** "):
        return build_heading(1, line[2:])
    if line.startswith("** ") and not line.startswith("*** "):
        return build_heading(2, line[3:])
    if line.startswith("*** "):
        return build_heading(3, line[4:])
    if line.startswith("> "):
        return build_quote_block(line[2:])
    if line.strip() == "---":
        return build_divider()
    if line.startswith("- "):
        return build_bullet(line[2:])
    stripped = line.lstrip()
    if stripped and stripped[0].isdigit():
        m = re.match(r"^(\d+[.)])\s+(.*)", stripped)
        if m:
            return build_numbered(m.group(2))
    return None
