# -*- coding: utf-8 -*-
"""
添加闪念块（向后兼容脚本）
已迁移核心逻辑至 append_im_blocks 及 add_record.py。
此脚本保留为了避免旧指令报错。

用法：
    python add_flash.py "闪念内容"
    python add_flash.py "闪念内容" --tag TAG --project PROJECT
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notion_helper import (
    check_required_config,
    make_paragraph_block,
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
        output_error("ARGS", "缺少闪念内容")
        return

    text = " ".join(remaining)

    blocks = [make_paragraph_block(text)]
    append_im_blocks(blocks, type_key="flash", tag=tag, project=project)
    output_ok(f"已添加闪念：{remaining[0]}")


if __name__ == "__main__":
    main()
