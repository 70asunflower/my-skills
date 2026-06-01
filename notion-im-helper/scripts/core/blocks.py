"""Block builders and type configs — generic, no user-specific data."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

RICH_TEXT_CHUNK_SIZE = 1900  # Notion API limit: 2000 chars per rich_text object


def split_rich_text(text, chunk_size=RICH_TEXT_CHUNK_SIZE):
    """Split text into multiple rich_text objects to avoid Notion's 2000-char limit.

    Notion API allows up to 100 rich_text objects per block,
    each with a max of 2000 chars in text.content.
    We use chunk_size=1900 to leave a safety margin.
    """
    if len(text) <= chunk_size:
        return [{"type": "text", "text": {"content": text}}]
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append({"type": "text", "text": {"content": text[i:i + chunk_size]}})
    return chunks


# ---- Block builders ----

def build_paragraph(text, color="default"):
    """Build a paragraph block with rich_text."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": split_rich_text(text),
            "color": color,
        },
    }


def build_callout(emoji, text, color="default", children=None):
    """Build a callout block with optional children for multi-paragraph content.

    Notion API ignores \\n in rich_text content. To display multi-line text
    properly inside a callout, we put the first line/paragraph in the callout's
    own rich_text, and subsequent paragraphs as children paragraph blocks.
    """
    block = {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": split_rich_text(text),
            "color": color,
        },
    }
    if children:
        block["callout"]["children"] = children
    return block


def build_todo(text, checked=False):
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": split_rich_text(text),
            "checked": checked,
            "color": "default",
        },
    }


def build_bookmark(url, caption=None):
    """Build a bookmark block. Notion API only supports 'url' and 'caption' fields.

    Note: bookmark block does NOT have a 'rich_text' field like text blocks.
    Use 'caption' (rich_text array) for description text.
    The title/description/thumbnail are auto-fetched by Notion from the URL.
    """
    bookmark_data = {"url": url, "caption": []}
    if caption:
        bookmark_data["caption"] = split_rich_text(caption)
    return {
        "object": "block",
        "type": "bookmark",
        "bookmark": bookmark_data,
    }


def build_heading(level, text):
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {
            "rich_text": split_rich_text(text),
            "color": "default",
        },
    }


def build_quote_block(text):
    return {
        "object": "block",
        "type": "quote",
        "quote": {"rich_text": split_rich_text(text), "color": "default"},
    }


def build_divider():
    return {"object": "block", "type": "divider", "divider": {}}


def build_bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": split_rich_text(text), "color": "default"},
    }


def build_numbered(text):
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {"rich_text": split_rich_text(text), "color": "default"},
    }


def build_toggle(text, children=None):
    block = {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": split_rich_text(text),
            "color": "default",
        },
    }
    if children:
        block["toggle"]["children"] = children
    return block


def build_image_block(file_upload_id, caption=None):
    """Build an image block using a file_upload ID from Notion's File Upload API.

    After uploading a file via notion-upload, the returned file_id is used
    with type "file_upload" to attach the image to a block.
    """
    image_data = {
        "type": "file_upload",
        "file_upload": {"id": file_upload_id},
    }
    if caption:
        image_data["caption"] = split_rich_text(caption)
    return {
        "object": "block",
        "type": "image",
        "image": image_data,
    }


def build_image_block_external(url, caption=None):
    """Build an image block referencing an external URL."""
    image_data = {
        "type": "external",
        "external": {"url": url},
    }
    if caption:
        image_data["caption"] = split_rich_text(caption)
    return {
        "object": "block",
        "type": "image",
        "image": image_data,
    }


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
    "image": {"emoji": "🖼️", "color": "default", "label": "图片"},
}
