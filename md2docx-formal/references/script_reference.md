# 脚本说明（md2docx-formal 四件套）

> 本文件是技能的"代码说明书"。转换器逻辑、可调参数、通用/文档专属边界、校验与审计脚本
> 的判定规则都在此。改脚本前先读这份，避免破坏保真。

---

## 1. `convert_doc.py` —— 主转换器

**作用**：把 Markdown 源按"篇/章/节"语义转成规范 Word（python-docx 实现），
100% 内容保真，引用 `[n]` 上标，封面/目录/页眉页脚齐备。

**用法**
```bash
python convert_doc.py <source.md> <output.docx> \
    [--title "文档主标题"] [--no-toc] [--no-header-footer]
```

### 1.1 文件顶部可调常量（改这里调整排版，不碰逻辑）

| 常量 | 当前值 | 含义 |
|---|---|---|
| `CN` | 宋体 | 正文中文字体 |
| `HEI` | 黑体 | 标题字体 |
| `FANG` | 仿宋 | 引用块/摘字体 |
| `EN` | Times New Roman | 正文中英文字体 |
| `CODE` | Consolas | 代码段等宽字体 |
| `PAGE_W/H` | 21×29.7 cm | A4 |
| `MARGIN_*` | 上3/下2.5/左2.5/右2.5 cm | 页边距 |
| `HEADING_SPEC` | dict | 各样式 (字体, 字号pt, 加粗)：Heading1=16/Heading2=14/Heading3=12/Heading4=12/Heading5=10.5/Title=22（封面主标题实际在 `main()` 里用 28pt 覆盖）；H1–H3 加粗 |
| `CITATION_RE` | `\[\d+(?:[\s,，\-]+\d+)*\]` | 引用序号正则：`[1]`/`[1,2]`/`[1-3]`/`[1, 2]`/`[1，2]` |

### 1.2 关键函数

| 函数 | 职责 |
|---|---|
| `set_run_font(run, cn, en, size, bold, italic, color)` | 统一设置 run 的 ascii/eastAsia/hAnsi 字体与字号。**所有 run 都走它**，保证中文 `eastAsia` 不被漏（这是规避 Word「全选改字体」坏字体的根因） |
| `add_superscript_run(...)` | 生成一个带上标 `w:vertAlign=superscript` 的 run |
| `_add_plain` / `_add_cit_segments` | 把纯文本里的引用序号切成上标；`IN_REFERENCES=True` 时整段不转上标（参考文献章节内保持正体） |
| `add_list(items, numbered)` | 渲染列表。`numbered=True`：保留源 markdown 字面 `N. ` 前缀，渲染为 `Normal` 段落 + 悬挂缩进 `left_indent=0.63cm / first_line_indent=-0.63cm`（不依赖 Word 自动编号，避免跨列表续号）。`numbered=False`：用 `List Bullet` 样式。 |
| `_fix_bullet_style(doc)` | 遍历 numbering XML，把 bullet 级别的 `lvlText` 改为 `•`(U+2022)，并**同步把 `rFonts` 从 `Symbol` 改为标准字体**（`EN`=Times New Roman, `CN`=宋体）。只改字符不改字体 → □ 方框；两者都改 → 正确渲染。 |
| `add_runs(p, text, ...)` | **行内解析核心**：处理 `**加粗**`、`*斜体*`、`` `代码` ``、`[链接](url)`，并在非代码/非参考文献区把 `[n]` 上标化 |
| `style_setup(doc)` | 初始化 Normal（宋体/12pt/1.5倍/首行缩进2字）与各标题样式 |
| `_heading_style(md_level, text)` | **唯一文档专属函数**，见 1.3 |
| `add_heading` | 调 `_heading_style` 取样式；遇"参考文献"标题置 `IN_REFERENCES=True`，遇下一个 Heading 1 置 False |
| `add_table(tbl_lines)` | markdown 表格 → 真表格；首行表头加粗 + 浅蓝底纹；居中；列宽均分 |
| `render_meta_block(mlines, center)` | 封面/摘要区解析：连续 `|` 行→真表格，其余→段落 |
| `add_toc` / `add_field` | 插入 TOC 域（`TOC \o "1-3" \h \z \u`）+ 占位提示文字 |
| `add_header_footer(doc, title)` | 页眉=标题(9pt+下边框)；页脚=`第 X 页 / 共 Y 页`（PAGE/NUMPAGES 域） |
| `main()` | 流水线：解析封面 → 摘要页 → 目录页 → 正文逐行渲染 → 写页眉页脚 → 打印统计 |

### 1.3 `_heading_style(md_level, text)` —— 文档专属映射（唯一需微调处）

按"篇/章/节"语义而非 `#` 数量判定。规则（与代码一致）：

| 条件 | 映射 | 备注 |
|---|---|---|
| `md_level <= 1` | Heading 1 | 任何 `#` 顶层标题 |
| `第[一二三四五六]篇` | Heading 1 | 置 `CUR_PARENT='篇'` |
| `附录 [A-E]` | Heading 1 | 置 `CUR_PARENT='附录'` |
| `适用对象`/`数据可信度声明`/`适用边界声明`/`全文结构说明` | Heading 1 | 前置声明，置 `CUR_PARENT='前置'` |
| `第\d+章` 或 任意 `md_level==2` | Heading 2 | 兜底：所有 `##` 都归 H2 |
| `第二篇摘要` | Heading 2 | |
| `篇` 父级且含`导读` | Heading 2 | 如"第二篇导读" |
| `附录` 父级且 `^[A-E]\.\d` | Heading 2 | 附录直属章节 |
| `^[一二三四五]、` | Heading 2 | 如"一、二、三、" |
| `^\d+\.\d+`（审计项 10.1） | Heading 3 | `md_level==4` 时升级 |
| `^G\d`（缺口项 G1-R…） | Heading 3 | |
| 附录内 `概览`/`[一二三四五]、`/`主制造商分布`/`分类规则说明` | Heading 2 | |
| 附录内 `缺口总结` | Heading 3 | |
| 其余 `md_level==3` | Heading 3 | |
| 其余 `md_level==4` | Heading 4 | |
| 其余 | Heading 5 | |

> **适配新文档**：若换一份结构不同的中文报告，只需改本函数里的正则与分支
> （通常 5 分钟）。流水线、字体、引用上标、封面、表格等其余部分完全不用动。

### 1.4 通用 vs 文档专属

- **通用（开箱即用）**：CLI 参数、页面/字体/行距、TOC 域、页眉页脚、引用上标+保护逻辑、
  封面解析（拆"——"、表格、作者/版本/日期）、表格/引用块/列表（有序列表字面 `N. ` 前缀
  + 悬挂缩进 0.63cm，无序列表 `•` + 非 Symbol 字体）、100% 保真。
- **文档专属（仅 `_heading_style`）**：篇/附录/前置声明的精确命名、缺口项 `G*`
  、"第二篇导读/摘要"等专属章节名。

---

## 2. `verify_superscript.py` —— 引用上标核验

**作用**：确认 `[n]` 上标符合 GB/T 7714 顺序编码制。

**用法**
```bash
python verify_superscript.py <file.docx>
```
**退出码**：`0`=通过，`1`=存在违规，`2`=参数错误。

**判定逻辑**
1. **参考文献章节区间** `[ref_start, ref_end)`：第一个**含"参考文献"的 Heading** 起，到下一个
   **Heading 1** 止（避免把后面的附录也算进参考文献章节——早期版本曾因此误报）。
2. 遍历所有 run：
   - 区间内且为上标 → `viol_in_ref`（**应=0**，条目序号不该上标）
   - 区间外且非上标 → `viol_out`（**应=0**，正文/附录引用必须上标）
   - 区间外且上标 → `body_sup`（计数，仅展示）
3. **参考文献表**（首格文本=`编号` 的表）：表内 `[n]` 必须全平体 → `table_viol`（**应=0**）。

**通过条件**：`viol_in_ref == 0 and viol_out == 0 and table_viol == 0`。

---

## 3. `audit_docx.py` —— 格式审计

**作用**：结构化扫描 docx，输出可定位的问题清单。

**用法**
```bash
python audit_docx.py <file.docx> [--source <source.md>] [--checks "词1,词2"]
```

**检查项**
| 段 | 内容 |
|---|---|
| A | 标题层级统计 + Word 自动编号(`numPr`)检测（双重编号风险，**应=0**） |
| B | 各级标题实际字体/字号集合（应各自唯一） |
| C | 正文(Normal) run 字体/字号集合 |
| D | TOC 域存在？页眉文字？页脚含 PAGE/NUMPAGES 域？页面尺寸 |
| E | 表格数量 |
| F | （仅 `--source`/`--checks` 时）保真度：源标题数 vs docx 标题数（差 1 通常是主标题转 `Title` 样式，非丢失）；`--checks` 关键词是否都在文中 |

**注意**：F 段"标题数差"若 =1，多为**主标题**被渲染成 `Title` 样式（不计入 `Heading`），
属正常；若差很多，才是漏转。保真以"内容 100% 一致"为准，标题样式的 1 点差异不计为错误。

---

## 4. `verify_fidelity.py` —— 源 md ↔ docx 内容一致性审查

**作用**：逐块保真核验，能定位到"哪一句/哪个单元格"没转进去或被改动。
与 `audit_docx.py` 的 F 段（只看标题数 + 硬编码关键词）不同，这是真正的内容比对。

**用法**
```bash
python verify_fidelity.py <source.md> <output.docx> [--show N]
```
**退出码**：`0`=内容一致(无缺失)，`1`=存在缺失，`2`=参数错误。

**判定逻辑**
1. **正向覆盖（源 → docx，主判定）**：把源里每个文本单元（标题/段落/表格单元格/引用块/
   列表项）规范化后，检查是否作为子串出现在 docx 全文中；任一缺失即失败。
   按 `head/para/cell/quote/list` 分类统计命中/缺失，并给出覆盖率。
2. **反向抽查（docx → 源，信息性）**：把 docx 正文里 squeeze 后 ≥8 字的段落回查源文本，
   列出疑似"新增/编造"内容；白名单排除转换器自加的封面/目录/页眉页脚模板
   （`BACK_WHITELIST`：日期、目录、"更新域"占位、页脚"第 X 页/共 Y 页"等）。

**文本规范化（严格对齐转换器搬运方式，避免假警报）**
- 链接 `[text](url)` → 只保留 `text`（url 被转换器丢弃）
- 去掉 `**加粗**` / `*斜体*` / `` `代码` `` 标记，保留内部文字
- 表格按单元格拆分，分隔行 `|---|` 跳过；引用序号 `[n]` 原样保留（只被上标，字符仍在）
- 比对时压缩所有空白（`squeeze`），容忍换行/run 拆分/首行缩进差异
- **docx 全文额外纳入页眉/页脚**：封面标题被 `——` 拆成主/副两段（不含 `——`），
  完整标题只在页眉里连续出现，故必须纳入页眉才能匹配源里的完整标题行

**通过条件**：正向缺失数 == 0（覆盖率 100%）。反向抽查仅提示，不计入失败。

---

## 5. 运行依赖

- `python-docx`（`pip install python-docx`）。推荐用带该包的 venv：
  `python -m venv venv && venv/bin/pip install python-docx`。
- 三个脚本均纯 python-docx，不依赖 `editor_sdk`/Office 后端，沙箱内可直接跑。
