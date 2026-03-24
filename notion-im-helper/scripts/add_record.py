# -*- coding: utf-8 -*-
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
    # 提取特有的 --type 参数
    type_key = "diary" # 默认类型
    new_args = []
    i = 0
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            type_key = args[i + 1]
            i += 2
        else:
            new_args.append(args[i])
            i += 1

    remaining, tag, project = parse_metadata_args(new_args)

    if not remaining:
        output_error("ARGS", "缺少记录内容")
        return

    text = " ".join(remaining)

    blocks = [make_paragraph_block(text)]
    append_im_blocks(blocks, type_key=type_key, tag=tag, project=project)
    output_ok(f"已添加记录（{type_key}）：{text[:15]}...")

if __name__ == "__main__":
    main()
