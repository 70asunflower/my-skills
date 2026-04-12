#!/usr/bin/env python3
"""
screenshot.py — Infographic card HTML → PNG export via Playwright
Usage:
    python screenshot.py <path-to-html> [--output <output-png>] [--viewport 900x1200] [--scale 2]
"""

import argparse
import sys
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Screenshot an infographic HTML card as PNG")
    parser.add_argument("html_path", help="Path to the HTML file")
    parser.add_argument("--output", "-o", help="Output PNG path (default: <html>_card.png)")
    parser.add_argument("--viewport", "-v", default="900x1200",
                        help="Viewport size as WxH (default: 900x1200)")
    parser.add_argument("--scale", "-s", default="2",
                        help="Device pixel ratio / scale factor (default: 2, use 3 for Retina quality)")
    args = parser.parse_args()

    html_path = Path(args.html_path).resolve()
    if not html_path.exists():
        print(f"Error: HTML file not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = html_path.with_name(html_path.stem + "_card.png")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright not installed.", file=sys.stderr)
        print("Run: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    w, h = map(int, args.viewport.split("x"))
    scale = int(args.scale) if args.scale else 2

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": w, "height": h},
            device_scale_factor=scale,
        )
        page.goto(f"file:///{html_path.as_posix()}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()

    print(f"Saved: {output_path}")

if __name__ == "__main__":
    main()
