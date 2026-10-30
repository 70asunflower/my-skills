# -*- coding: utf-8 -*-
"""Whole-doc surgery pipeline for SiYuan — the tested implementation of
SKILL.md Q1 (Fix A), Q2 (zero-width set), Q12/Q13, Q20.

Pipeline: export baseline -> ZWSP-tolerant substring replacement (assert
exactly-one hit each) -> Fix A whole-doc replace (delete children, assert
empty, updateBlock once) -> fresh-export dual-marker verification (mine +
the user's content).

Import-use (needs scripts/sy.py next to it):

    import sys; sys.path.insert(0, r"<skill dir>/scripts")
    from sy import connect, call
    from siyuan_surgery import (export_body, replace_pairs, fix_a_replace,
                                verify_markers)
    base, token = connect()
    raw = export_content(base, token, DOC_ID)
    md = export_body(raw)                      # strips frontmatter + H1 decor
    new = replace_pairs(md, [(old, new), ...])
    fix_a_replace(base, token, DOC_ID, new)
    verify_markers(base, token, DOC_ID, mine=[...], theirs=[...])
"""

import re
import time

# Q2: full zero-width / invisible set to strip before comparing content.
ZW_CHARS = ("\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
            "\u2060\u2061\u2062\u2063\u2064\ufeff\u061c\u034f")
ZW_CLASS = "[" + re.escape(ZW_CHARS) + "]"


def strip_zw(s):
    return re.sub(ZW_CLASS, "", s)


def zx(old):
    """Regex matching `old` with optional invisible chars between any two
    characters (Lute's inline-node guards in exported markdown, Q11)."""
    sep = "(?:" + ZW_CLASS + ")*"
    return sep.join(re.escape(ch) for ch in old)


def export_content(base, token, doc_id):
    """Fresh export of the whole doc as markdown (frontmatter included)."""
    from sy import call
    return call(base, token, "/api/export/exportMdContent", {"id": doc_id})["content"]


def export_body(raw, drop_h1=True):
    """Strip export decorations: YAML frontmatter and the auto-generated
    leading `# Title` line (the block tree has neither)."""
    body = raw
    if body.startswith("---\n"):
        end = body.find("\n---", 4)
        if end != -1:
            body = body[body.find("\n", end + 1) + 1:]
    body = body.lstrip("\n")
    if drop_h1 and body.startswith("# "):
        body = body[body.find("\n") + 1:]
    return body.lstrip("\n")


def replace_pairs(md, pairs):
    """Apply literal (old, new) replacements, each asserted to hit exactly
    once. Returns the new text; raises with a per-pair report on failure —
    nothing is written to SiYuan by this function."""
    failed = []
    for i, (old, new) in enumerate(pairs):
        md2, n = re.subn(zx(old), lambda _m, _n=new: _n, md)
        if n == 1:
            md = md2
        else:
            failed.append((i, n, old[:60]))
    if failed:
        report = "\n".join(f"  #{i} hits={n}: {head}" for i, n, head in failed)
        raise RuntimeError(f"{len(failed)}/{len(pairs)} pairs failed "
                           f"(0 = not found, >1 = ambiguous):\n{report}")
    return md


def _is_drained(kids):
    """Q13/Q19: after deleting all children SiYuan regenerates exactly one
    zero-length `p` as a placeholder — that (or truly empty) is drained."""
    if not kids:
        return True
    return (len(kids) == 1 and kids[0].get("type") == "p"
            and not (kids[0].get("markdown") or "").strip())


def fix_a_replace(base, token, doc_id, md, max_rounds=5, confirm_children=None):
    """Q1 Fix A, hardened per Q13: delete every child, re-read until the doc
    is drained (empty, or SiYuan's regenerated placeholder `p`), only then
    updateBlock ONCE with the full new markdown. Non-empty survivors beyond
    the placeholder raise. `confirm_children(doc_id)` is an optional
    pre-flight check."""
    from sy import call

    def children():
        return call(base, token, "/api/block/getChildBlocks", {"id": doc_id})

    if confirm_children is not None:
        confirm_children(doc_id)
    before = len(children())
    for _round in range(max_rounds):
        kids = children()
        if _is_drained(kids):
            break
        for b in kids:
            call(base, token, "/api/block/deleteBlock", {"id": b["id"]})
        time.sleep(0.5)
    else:
        survivors = [(b["id"], b.get("type"), (b.get("markdown") or "")[:40])
                     for b in children() if not _is_drained([b])]
        raise RuntimeError(f"children not drained after {max_rounds} delete "
                           f"rounds (Q13): {survivors}")
    call(base, token, "/api/block/updateBlock",
         {"id": doc_id, "dataType": "markdown", "data": md})
    return before


def verify_markers(base, token, doc_id, mine, theirs=None):
    """Q20 dual-marker check on a FRESH export, invisible chars stripped.
    Returns dict with the missing lists — empty means verified."""
    t = strip_zw(export_content(base, token, doc_id))
    return {
        "missing_mine": [m for m in mine if m not in t],
        "missing_theirs": [m for m in (theirs or []) if m not in t],
        "note_count": t.count("> [!NOTE]"),
        "chars": len(t),
    }
