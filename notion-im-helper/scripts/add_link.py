# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notion_helper import (
    check_required_config,
    append_im_blocks,
    output_ok,
    output_error,
    parse_metadata_args,
)

def make_bookmark_block(url: str) -> dict:
    return {
        "object": "block",
        "type": "bookmark",
        "bookmark": {
            "url": url
        }
    }

def main():
    if not check_required_config():
        return

    args = sys.argv[1:]
    remaining, tag, project = parse_metadata_args(args)

    if not remaining:
        output_error("ARGS", "缺少网址内容")
        return

    url = remaining[0].strip()

    blocks = [make_bookmark_block(url)]
    append_im_blocks(blocks, type_key="link", tag=tag, project=project)
    output_ok(f"已添加网页书签：{url[:30]}...")

if __name__ == "__main__":
    main()
