"""Core modules — generic, portable, no user-specific data."""
from .blocks import (
    split_rich_text,
    build_paragraph, build_callout, build_todo, build_bookmark,
    build_heading, build_quote_block, build_divider,
    build_bullet, build_numbered, build_toggle,
    build_image_block, build_image_block_external,
    TYPE_CONFIG,
)
