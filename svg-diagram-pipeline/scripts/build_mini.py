# -*- coding: utf-8 -*-
"""把可视化片段（HTML 片段，无 doctype）包成可截图的 mini HTML。
用法: python build_mini.py <fragment.html> <mini.html>"""
import sys
from pathlib import Path

if len(sys.argv) != 3:
    sys.exit("usage: python build_mini.py <fragment.html> <mini.html>")

frag = Path(sys.argv[1])
mini = (
    '<!doctype html>\n<html><head><meta charset="utf-8">\n'
    "<style>html,body{margin:0;padding:0;background:#ffffff;}</style>\n"
    "</head><body>\n" + frag.read_text(encoding="utf-8") + "\n</body></html>\n"
)
Path(sys.argv[2]).write_text(mini, encoding="utf-8")
print("mini written:", sys.argv[2])
