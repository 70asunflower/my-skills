---
name: strict-docx-audit
description: Post-conversion comprehensive docx quality gate — 12 checks
  covering bullet font, list numbering, superscript, fidelity (hard-fail),
  heading hierarchy, tables, fonts, TOC/header/footer, page layout, eastAsia
  integrity, and empty paragraphs. Defaults tuned for Chinese engineering papers
  (A4/GB/T 7714); all thresholds configurable at script top. Use after every
  conversion before delivery.
agent_created: true
---

# strict-docx-audit — docx 严格审查

## Purpose

Run a comprehensive **12-check audit** on any `.docx` file (defaults tuned for Chinese
engineering papers) and produce a unified pass/fail report.

## Generality

- All page dimensions, margins, font names, and thresholds are **configurable constants**
  at the top of `strict_audit.py`. Change them for non-A4 documents, English papers, etc.
- All checks are content-agnostic — no hard-coded document titles, chapter names, or
  section labels. The only China-specific default is the `参考文献` heading name for
  superscript detection (works for any GB/T 7714 sequential-cited paper).
- Works with any Markdown→DOCX converter, not just `md2docx-formal`. Check 5 (fidelity)
  auto-locates `verify_fidelity.py` if `md2docx-formal` is installed; skips gracefully
  if not found.
Catches the most common conversion bugs before delivery — from the ones we've actually hit
(bullet squares, list numbering continuation) to frequent but subtle issues (missing eastAsia,
code/quote font mismatch, table header formatting).

## When to use

- Right after `convert_doc.py` finishes
- After source Markdown changes and re-conversion
- Before delivering the `.docx` to anyone

## 🔒 Mandatory execution protocol (DO NOT SKIP OR ABBREVIATE)

When this skill is invoked, you MUST follow this protocol **exactly** — no shortcuts, no
selective checking, no "looks fine I'll skip the rest":

1. **Create a task list** with one task per check ([1] through [12]).
2. **Run the full 12-check audit** via `python strict_audit.py OUTPUT.docx --source SOURCE.md`.
   Never run individual checks manually or selectively.
3. **Read ALL output.** Do not stop reading after the first failure or after the summary table.
   Every check line must be consumed.
4. **Mark each task** in the task list as completed, with its status (✅ / ❌ / ⚠).
5. **If any ❌**: report which checks failed, what they mean, and how to fix.
   Do NOT deliver the docx until all ❌ are resolved.
6. **If `--strict` mode**: ⚠ warnings also block delivery.

**HARD RULE**: The audit script exits with code 0 only when all ❌ checks pass.
Trust the exit code — do not second-guess it or skip re-running after a fix.

## Usage

```bash
python scripts/strict_audit.py OUTPUT.docx [--source SOURCE.md] [--skip-fidelity]
```

- Exit code `0` = all checks pass
- Exit code `1` = one or more failures
- `--source` enables [5] fidelity check (skips if omitted)

## 12 检查全览

| # | 检查 | 类型 | 检测什么 | 可调常量 |
|---|------|------|----------|----------|
| [1] | Bullet 字体 | ❌ 阻断 | Symbol 字体 → `•` 变方框 □ | — |
| [2] | List Number 段落 | ❌ 阻断 | Word 内置自动编号残留 → 跨列表续号 | — |
| [3] | 有序列表编号 | ⚠ 信息 | 每组编号是否从 1 开始 | — |
| [4] | 引用上标 | ❌ 阻断 | GB/T 7714：正文 `[n]` 上标 / 参考文献平体 | — |
| [5] | 内容保真 | ❌ 阻断 | 委托 verify_fidelity 逐块比对，<100% 即失败 | — |
| [6] | 标题层级 | ❌ 阻断 | numPr 双重编号 + H1-H5 统计 | — |
| [7] | 表格审计 | ⚠ 信息 | 表头加粗率 / 空单元格 | `TABLE_HEADER_BOLD_RATIO` `TABLE_EMPTY_CELL_RATIO` |
| [8] | 引用块字体 | ⚠ 信息 | Quote 段字体一致性 | `EXPECTED_QUOTE_FONT` |
| [9] | TOC / 页眉页脚 | ⚠ 信息 | TOC 域 + PAGE/NUMPAGES 域 | — |
| [10] | 页面布局 | ⚠ 信息 | 纸张尺寸 / 页边距 | `PAGE_W/H_CM` `MARGIN_*_CM`（None=跳过） |
| [11] | 中文字体完整性 | ❌ 阻断 | eastAsia 是否被清空 | — |
| [12] | 空段落 | ⚠ 信息 | ≥N 连续空段 | `EMPTY_PARAGRAPH_THRESHOLD` |

- ❌ 失败 = 触发退出码 1，应修复后重转
- ⚠ 信息 = 仅报告，不触发失败（可能是正常场景）

## Key design decisions

- **[3] ordered lists**: informational — continuous numbering across sub-sections is legitimate.
- **[5] fidelity**: **hard fail** when `--source` is provided. Delegates to
  `verify_fidelity.py` (auto-located via relative path). Skips without `--source`.
- **[8] quote font**: informational — change `EXPECTED_QUOTE_FONT` at script top.
- **[10] page layout**: tunable — set any margin to `None` to skip; set `PAGE_W_CM=None`
  to skip entire page check.
- **[11] eastAsia**: correctly skips runs that inherit from paragraph style; only flags
  runs where eastAsia was explicitly wiped (the "全选改字体" symptom).
- All ⚠ checks are informational; only ❌ checks block delivery.
- Pure `python-docx` — sandbox-compatible, no Word/Office dependency.

## Output example

```
=================================================================
  docx 严格审查报告
  C:/path/to/output.docx
=================================================================

[1]  Bullet 字体（□ 方框）
  ✅ 通过 — 4 个 bullet 级别，0 Symbol

[2]  List Number 段落（续号）
  ✅ 通过 — 0 条 List Number 段落

[3]  有序列表编号
  ⚠ 3/16 组不是从 1 开始（可能源文件连续编号，属正常）

[4]  引用上标（GB/T 7714）
  ✅ 通过 — 正文上标 68，误标 0，漏标 0

[5]  内容保真
  合计 2338 个单元，命中 2338，缺失 0，覆盖率 100.00%
  结论: ✅ 内容一致（源无遗漏）

[6]  标题层级
  H1=10  H2=36  H3=61  H4=11  H5=23
  ✅ numPr=0

[7]  表格审计
  表数量: 45
  ✅ 通过

[8]  代码 & 引用块字体
  ✅ 引用块字体正确 (14 个 Quote 段落)

[9]  TOC & 页眉页脚
  ⚠ 未找到 TOC 域（可能未生成目录页）
  ✅ 页脚含 PAGE + NUMPAGES 域

[10] 页面布局
  ✅ A4 + 标准边距

[11] 中文字体完整性（eastAsia）
  ✅ 通过 — 362 个含中文段落 eastAsia 完整

[12] 空段落
  ⚠ 1 处连续空段落（≥3个）

=================================================================
  ✅ 全部检查通过
=================================================================
```

## Pipeline integration

```
源 .md  ──convert_doc.py──▶  .docx
                               │
                               ▼
                        strict_audit.py
                               │
                       ┌───────┴───────┐
                       ▼               ▼
                    ✅ 通过          ❌ 失败
                    → 交付          → 修复 → 重转 → 重审
```
