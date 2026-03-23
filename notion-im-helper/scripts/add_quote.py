# -*- coding: utf-8 -*-
"""
添加引用块

用法：
    python add_quote.py "引用内容"
    python add_quote.py "引用内容" --tag TAG --project PROJECT
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notion_helper import (
    check_required_config,
    make_quote_block,
    append_im_blocks,
    output_ok,
    output_error,
    parse_metadata_args,
)


def main():
    if not check_required_config():
        return

    args = sys.argv[1:]
    remaining, tag, project = parse_metadata_args(args)

    if not remaining:
        output_error("ARGS", "缺少引用内容")
        return

    text = " ".join(remaining)

    blocks = [make_quote_block(text)]
    append_im_blocks(blocks, type_key="quote", tag=tag, project=project)
    output_ok(f"已添加引用")


if __name__ == "__main__":
    main()
