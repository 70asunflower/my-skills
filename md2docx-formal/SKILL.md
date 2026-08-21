---
name: md2docx-formal
description: "Convert Markdown into a formally typeset Chinese engineering Word (.docx) document using python-docx. This skill should be used when the user wants to turn a Markdown paper/report/thesis into a submission- or archive-quality Word file with structured heading hierarchy (H1-H5) mapped by 篇/章/节 semantics, A4 page layout, 宋体/黑体 fonts, 1.5x line spacing, auto table of contents field, header/footer with page numbers, and reference citations [n] rendered as superscripts per GB/T 7714 sequential-coding style while keeping the 参考文献 list entries in normal size. Also use it to re-verify, re-audit, or run a block-level source-to-docx consistency/fidelity check (一致性审查) on an existing docx after the source Markdown changes."
agent_created: true
---

# md2docx-formal — Markdown → 规范 Word 工程文档

## Purpose

Turn a Chinese Markdown paper / report / thesis into a formally typeset `.docx` that meets
common submission/archive conventions, with **100% content fidelity** (no fabrication, no
addition/deletion). The converter is python-docx based and reproducible: change the source
Markdown, re-run, re-verify.

## When to use

- "把这份 md 转成正式 Word 文档 / 排个版"
- "内容更新了，重转 docx" / "重新生成 Word"
- "引用序号要上标" / "检查目录、页眉页脚、标题层级"
- Any task that maps a Markdown source to a typeset Chinese Word deliverable.

## Script reference

Full script internals — functions, tunable constants, generic vs document-specific boundaries,
and the verification/audit logic — are documented in
[`references/script_reference.md`](references/script_reference.md). Read it before editing any
script so you don't break content fidelity.

## Pre-flight check: ASCII 图（转换前必查）

扫描源 Markdown 的围栏代码块：若出现**框线/箭头字符密集**的内容（`─│┌┐└┘├┤┬┴┼▼►` 等，
典型为拓扑图 / 部署图 / 信号链路图 / 流程图），这是 ASCII 字符画——**必须主动提醒用户**：

1. ASCII 字符画直接转 docx 只能得到等宽文本块，观感差且不正式；
2. 建议用 **`fireworks-tech-graph` skill** 将其重绘为正式 SVG/PNG（该 skill 会做几何校验与视觉审查）；
3. 重绘后以 `![题注](图片.png)` 语法替换 ASCII 代码块（转换器已支持图片渲染：居中、15cm 等比缩放、题注）；
4. PNG 与 md 放同目录（相对路径引用），然后重新执行转换。

转换器运行时也会自动检测并打印同类提醒（`[提示] 检测到疑似 ASCII 字符画…`），见 `_looks_like_ascii_art()`。
用户明确表示"就保留 ASCII"时尊重其选择，转换照常进行。

## Pipeline (do this in order)

1. **Generate** with `scripts/convert_doc.py`:
   ```bash
   python scripts/convert_doc.py SOURCE.md OUTPUT.docx \
       [--title "文档主标题"] [--no-toc] [--no-header-footer]
   ```
   - `python` must be a venv with `python-docx` installed. If missing:
     `python -m venv venv && venv/bin/pip install python-docx`.
   - The first `# ` heading becomes the Title (overridable via `--title`).
   - **Cover page**: the title is split on `——` into a main title (28pt) + subtitle (16pt);
     the meta block between the title and the first `## ` is parsed — markdown tables become
     real centered tables (e.g. 项目属性), other lines (作者/版本/日期) become centered
     paragraphs. The cover is followed by a standalone 摘要 page, then the TOC page. See
     `references/format_spec.md` §2.5.
   - Heading levels are mapped by **篇/章/节 semantics**, not raw `#` count
     (see `references/format_spec.md` §3). If the document uses a different structure,
     tune the single function `_heading_style()` in `convert_doc.py`.
   - Citations `[n]` / `[n,m]` / `[n-m]` become **superscripts** in body/appendices;
     inside the 参考文献 section and inside code spans they stay literal. Details in
     `references/format_spec.md` §4.

2. **Verify citations** with `scripts/verify_superscript.py`:
   ```bash
   python scripts/verify_superscript.py OUTPUT.docx
   ```
   Expect: body citations all superscript, 参考文献-section entries all plain, 参考文献
   table all plain. Exit code 0 = pass.

3. **Audit format** with `scripts/audit_docx.py`:
   ```bash
   python scripts/audit_docx.py OUTPUT.docx \
       [--source SOURCE.md] [--checks "关键词1,关键词2"]
   ```
   Checks heading levels, double-numbering risk (numPr), heading/body fonts & sizes,
   TOC field, header/footer/page-number fields, page size, table count, and (with
   `--source`) heading-count diff + retained key terms.

4. **Consistency check** with `scripts/verify_fidelity.py` (源 md ↔ docx 逐块保真):
   ```bash
   python scripts/verify_fidelity.py SOURCE.md OUTPUT.docx [--show N]
   ```
   Block-level content audit that locates the exact sentence/cell if anything went
   missing. **Forward coverage** (source -> docx, the pass/fail criterion): every
   source text unit (heading / paragraph / table cell / quote / list item) must appear
   as a substring in the docx. **Backward spot-check** (docx -> source, informational):
   lists docx body paragraphs not found in the source (possible additions), whitelisting
   converter-added cover/TOC/header/footer templates (date, TOC placeholder). Exit 0 =
   no source content missing. Run this whenever the user asks for a 一致性审查 / 保真核验,
   or after every reconversion to prove 100% fidelity.

## Critical rules (do NOT violate)

- **NEVER modify the source Markdown.** The source is absolute-authority; if the docx looks
  wrong, it's a converter issue, not a source issue. Fix the converter, never the source.
- **Never "select all → change font" in Word.** That only rewrites `w:ascii`/`w:hAnsi`,
  not `w:eastAsia`, silently breaking Chinese fonts and flattening all sizes. Change
  fonts/sizes in the Markdown source and re-run the converter instead.
- **No Word auto multi-level numbering** (keep `numPr=0`). Manual "第N章 / 2.1" text is
  the sole numbering source; adding auto-numbering creates double numbering.
- **Ordered lists are literal "N. " text, NOT Word auto-numbering.** Using Word's built-in
  `List Number` style causes cross-list continuation (a later list resumes numbering from
  an earlier one). Instead, the converter preserves the source's literal `N. ` prefix as
  plain text in a `Normal`-style paragraph with a hanging indent of 0.63 cm. This guarantees
  each list matches the source exactly — no continuation, no fabrication.
- **Bullet lists use `List Bullet` with `•` (U+2022) + Times New Roman font.** `_fix_bullet_style()`
  changes both the bullet character AND the font: Word's default `List Bullet` uses the Symbol font
  with a private-use character; if only the character is changed to `•` but the font stays Symbol,
  Word renders an empty square (□) because Symbol has no glyph for U+2022.
- **Strict fidelity.** Do not invent, add, or drop any text, data, or term. Citations and
  figures must match the source exactly.
- **TOC is a field.** Tell the user to right-click "更新域" in Word to populate it; the
  placeholder text is intentional, not an error.
- Do not use the `tencent-local-office-edit` skill for this — its `editor_sdk` backend is
  unavailable in the sandbox and manual edits corrupt eastAsia fonts.

## Output notes

- Deliver the `.docx`. Optionally mirror to a versioned copy (`_v3.docx`) if the user keeps
  numbered drafts.
- After generation, report heading counts, table count, and the verify/audit summary to
  the user.
- If the source Markdown changes later, re-run step 1–3; no manual docx editing needed.
