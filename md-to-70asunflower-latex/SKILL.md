---
name: md-to-70asunflower-latex
description: 将 Markdown 技术博客或长篇技术手册转换为 70asunflower 风格 LaTeX 文档，适配 Overleaf XeLaTeX 编译。支持短博客、长文档、技术表格、代码块、公式、核心要点、面试常问与静态检查。
---

# Markdown 转 70asunflower LaTeX 博客模板 v2

## 目标

本 Skill 用于把 Markdown 技术文章转换成 70asunflower 个人品牌风格 LaTeX 文档。输出 `.tex` 文件应可上传 Overleaf，并使用 **XeLaTeX** 编译。

v2 重点增强：

- 长篇技术手册支持
- LaTeX 特殊字符转义规则
- 表格鲁棒性
- Markdown 手写目录跳过
- Part / Chapter 结构处理
- 核心要点与面试常问专用框
- 静态检查与项目化输出

## 文件结构

```text
md-to-70asunflower-latex/
├── SKILL.md
├── assets/
│   └── 70asunflower_blog_template.tex
├── references/
│   ├── conversion_rules.md
│   ├── latex_escape_rules.md
│   ├── long_document_rules.md
│   └── quality_check_rules.md
└── examples/
    ├── short_blog.md
    ├── long_manual.md
    └── expected_project_structure.txt
```

## 推荐输出项目结构

```text
project/
├── main.tex                         # 或文章名.tex
├── source.md                        # 原始 Markdown 副本
├── compile.bat                      # Windows / MiKTeX 一键编译（自动多遍）
├── compile.sh                       # Linux / macOS 一键编译（latexmk 或 xelatex x3）
├── latexmkrc                        # 强制 XeLaTeX + 足够遍数
├── STATIC_CHECK_REPORT.txt          # 静态检查报告
├── README.md                        # 编译说明（含“必须编译两遍”提示）
└── assets/                          # 图片等资源，可选
```

> `compile.bat` / `compile.sh` / `latexmkrc` 直接从 `assets/` 复制进生成项目即可（它们会自动识别目录里的主 `.tex`）。

## 转换流程

### Step 1：读取 Markdown 元信息

优先级：

1. YAML frontmatter
2. 第一个 `#` 标题
3. 开头 blockquote
4. 首个正文段落
5. 默认元信息

无 YAML 时默认：

```yaml
title: 第一个 # 标题
subtitle: 标题冒号后半部分，或根据内容自动生成
date: 当前年月
author: 70asunflower
tags: 根据关键词生成，或默认“技术博客”
abstract: 开头 blockquote 或首段
```

### Step 2：选择转换模式

#### short_blog

适合短篇博客：

```text
#  → \section
## → \subsection
### → \subsubsection
```

#### long_technical_manual

适合长篇技术手册，默认推荐：

```text
# 篇章标题 / Chapter / Part Title → partcard 或 \section
# 一级标题          → \section
## 二级标题        → \subsection
### 三级标题    → \subsubsection
#### 更小标题      → \paragraph
```

### Step 3：跳过 Markdown 手写目录

如果 Markdown 中存在：

```markdown
## 目录
- [xxx](#xxx)
...
---
```

默认跳过，不转换进正文。LaTeX 使用：

```latex
\tableofcontents
```

自动生成目录。

### Step 4：转换正文元素

核心规则见：`references/conversion_rules.md`。

### Step 5：执行 LaTeX 转义

普通文本和表格必须转义 `_ % & # $ { } ~ ^ \`。代码块和公式块不按普通文本转义。详细规则见：`references/latex_escape_rules.md`。

### Step 6：长文档增强

长文默认启用：

```latex
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{ragged2e}
\usepackage{xurl}
\usepackage{needspace}
\usepackage{fvextra}
\setcounter{tocdepth}{3}
\setcounter{secnumdepth}{0}
\linespread{1.08}
\emergencystretch=3em
\sloppy
```

详细规则见：`references/long_document_rules.md`。

### Step 7：静态检查

生成后必须检查：

- `\begin{...}` / `\end{...}` 是否配对
- 花括号是否平衡
- 是否残留 Markdown 代码围栏 ```
- 是否残留 Markdown 目录锚点 `](#...)`
- 是否出现 `\begincodebox`、`\beginlstlisting` 等拼接错误
- 是否出现乱码字符 `�`
- 表格是否可能超宽

详细规则见：`references/quality_check_rules.md`。



## 目录与章节编号规范

LaTeX 的 `\tableofcontents` 会自动输出目录标题，因此模板和转换器不要额外手写一个“目录”大标题，例如：

```latex
{\Large\bfseries\color{Primary}$\equiv$ 目录}
```

否则 PDF 可能出现重复目录标题。

对于源 Markdown 已经自带编号的长文档，推荐采用更通用、稳定的策略：

```latex
\setcounter{tocdepth}{3}      % 目录收录到三级标题，可按需调整
\setcounter{secnumdepth}{0}   % 不显示 LaTeX 自动编号
```

然后仍使用普通标题命令：

```latex
\section{源文档中的一级标题}
\subsection{源文档中的二级标题}
\subsubsection{源文档中的三级标题}
```

这样可以保留 Markdown 标题中自带的编号或命名方式，同时避免 LaTeX 再叠加一套自动编号；并且普通标题会自动进入目录、自动更新页眉，比大量 `\section* + \addcontentsline` 更稳。

如果源 Markdown 没有自带编号，也可以继续使用同一策略；标题会按原文展示，只是不显示 LaTeX 自动编号。若用户明确要求 LaTeX 自动编号，再把 `secnumdepth` 调回合适层级。

目录页码需要至少编译两次 XeLaTeX。

## 字体规范

模板应按内容类型使用常见字体族，而不是让中英数混用默认字体：

- 中文正文：优先 Noto Serif CJK SC / 思源宋体风格；回退 FandolSong。
- 中文黑体：优先 Noto Sans CJK SC / 思源黑体风格；回退 FandolHei。
- 英文与数字正文：TeX Gyre Termes / Times-like。
- 英文无衬线：TeX Gyre Heros / Helvetica-like。
- 代码：Latin Modern Mono / 等宽字体。
- 数学公式：保持 LaTeX 默认数学字体，避免普通 text 框伪装公式。

## 公式识别规范

无语言或 `text` 代码块不应一律转成 `codebox[Text]`。如果短代码块明显是公式，应转成 `mathbox`。

例如 Markdown：

```text
value = (-1)^sign × mantissa × 2^exponent
```

应转换为：

```latex
\begin{mathbox}
\[
\begin{aligned}
\mathrm{value} &= (-1)^{\mathrm{sign}} \times \mathrm{mantissa} \times 2^{\mathrm{exponent}}
\end{aligned}
\]
\end{mathbox}
```

识别建议：短块、无中文、包含 `=`/`≈`/`≤`/`≥`，并含有 `^`、`×`、`/`、`round`、`clamp`、`_` 等数学信号时，优先按公式处理。包含中文说明或流程图的 text 块继续保留为 `codebox[Text]`。

为避免误判，以下情况应仍作为代码保留，不要转公式：

- 赋值/配置型语句，如 `key = value`、`export X=1`、`lr = 0.001`（只有赋值号、无数学运算）。
- 函数调用为主的伪代码，如 `loss = model(x)`、`y = f(x)`（含函数调用但无指数/乘除/关系链）。
- 含路径、命令行参数、`->`、`=>`、`==` 等编程符号的行。

疑似代码时应保守处理（保留为代码框），宁可漏转也不要误转。

## 封面布局规范

封面 logo 必须单独占一行，避免和日期/作者元信息挤在同一行。推荐写法：

```latex
\begin{center}
  \sunflowerwatermark[100]{2.5}\par
  \vspace{0.45cm}
  {\small\color{gray!70}$\bullet$ 2026年6月}\par
  \vspace{0.12cm}
  {\small\color{gray!70}$\bullet$ 70asunflower}\par
  \vspace{0.12cm}
  {\small\color{gray!70}$\bullet$ 标签1, 标签2}\par
\end{center}
```

不要把 logo、日期、作者、标签写成同一个水平行。长标签较多时，标签行可以只保留 3-5 个关键词。

## 结尾页脚规范

文档末尾页脚只保留：

```latex
\textcolor{gray!60}{\small$\star$ 70asunflower \quad $\heartsuit$ 感谢阅读，欢迎交流}
```

不要添加额外平台宣传语。

## 编译说明

**核心铁律：目录（`\tableofcontents`）必须至少编译两遍 XeLaTeX。**
第一遍把标题写进 `.toc`（此时 PDF 目录仍为空，属正常现象，不报错）；第二遍读取 `.toc`，目录条目与页码才出现。
「目录空白 / 页码全是 0 / 页码不对」几乎都是因为只编译了一遍。这是本 skill 最常见的用户反馈，必须主动预防。

生成项目时**必须**一并放入 `compile.bat`、`compile.sh`、`latexmkrc`（从 `assets/` 复制），并在 README 顶部用醒目段落写明「目录为空 = 只编译了一遍，请编译两遍」。

各环境编译方式：

- **Overleaf**：Menu → Compiler 选 **XeLaTeX** → Recompile 两次；仍空白则 Menu → Clear cached files 后重编。（Overleaf 默认 latexmk，通常会自动多遍。免费版对超长文档可能超时，可建议本地编译。）
- **本地 Linux/macOS**：在项目目录运行 `bash compile.sh`（有 latexmk 用 latexmk，否则连跑 3 次 xelatex）。
- **本地 Windows / MiKTeX**：双击或在 MiKTeX 控制台运行 `compile.bat`（优先 `texify --engine=xetex` 自动多遍，否则跑两次 xelatex）。
  - **MiKTeX Portable 注意**：便携版通常不在系统 PATH 中，直接双击 `compile.bat` 可能报 “xelatex 不是内部或外部命令”。此时改从 **MiKTeX Portable 自带控制台**运行，或用 **TeXworks**（引擎选 XeLaTeX，点排版两次）。
  - 中文字体：模板优先 Noto CJK，未安装会自动回退 **Fandol**（MiKTeX 自带），中文可正常显示。

如果当前环境无 `xelatex`，仍应生成 `.tex`、README、编译脚本和静态检查报告，并说明未本地编译的原因——但绝不能省略「必须编译两遍」的提示。

## 模板自定义命令

- `\keyword{...}`：蓝色粗体关键词
- `\concept{...}`：紫色概念高亮
- `\highlight{...}`：橙色背景高亮
- `\codeinline{...}`：行内代码
- `\dtype{...}`：数据类型/格式，例如 FP16、INT8
- `\method{...}`：算法/方法，例如 GPTQ、AWQ

## 模板环境

- `covercard`：封面卡片
- `abstractcard`：摘要卡片
- `mathbox`：公式框
- `codebox`：代码框
- `tipbox`：提示框
- `warnbox`：警告框
- `quotebox`：引用框
- `partcard`：长文 Part 分隔卡片
- `keypointsbox`：核心要点框
- `interviewbox`：面试常问框

## 重要注意事项

- 不要在 `codebox` 内使用 `verbatim`，必须使用 `lstlisting`。
- 不要在普通文本中遗留未转义 `_ % & # $ { }`。
- 不要把无语言伪公式代码块强行转数学公式，除非内容是合法 LaTeX 数学表达。
- 长表格优先使用 `tabularx` 或 `longtable`。
- 目录由 LaTeX 自动生成，不要保留 Markdown 手写目录。


## 页眉与目录稳定性规范

**首选**：使用普通标题 `\section{...}` / `\subsection{...}` / `\subsubsection{...}`。配合 `\setcounter{secnumdepth}{0}`，既不会多出自动编号，也会自动进入目录、自动更新页眉 mark（模板已通过 `\sectionmark` 处理）。

只有在不得不使用星号标题 `\section*` 时，LaTeX 才不会自动更新页眉 mark，此时需在标题后手动补一句：

```latex
\markboth{当前章节标题}{}
```

模板页眉不要使用 `\thesection \leftmark`，否则在 `secnumdepth=0` 或星号标题下 `\thesection` 会显示为 `0`，右上角出现 `0 目录`。应使用：

```latex
\fancyhead[R]{\small\color{Primary}\leftmark}
```

长文档如果希望目录包含三级标题，应设置 `\setcounter{tocdepth}{3}`。目录页码需要至少编译两次 XeLaTeX。

## 数学变量与下划线规范

数学公式中如果出现带下划线的文本型变量名，例如 `identifier_name`、`token_count`、`cache_size`，应按语义选择：

```latex
\mathrm{identifier\_name}
```

或在单字母变量下标场景中写成：

```latex
x_{\mathrm{name}}
```

不要生成：

```latex
\mathrm{identifier\\_name}
```

因为 `\\` 在数学环境中会被 LaTeX 视为换行，导致变量名被错误拆开。

这条规则适用于所有带下划线的文本变量，不针对某一个具体词。

## 转换后核验规范（必须执行）

不能只检查 LaTeX 是否“不报错”。转换后必须做结构核验和视觉风险核验。

### A. 静态结构核验

必须生成 `CONVERSION_VERIFICATION_REPORT.txt`，至少检查：

- `\tableofcontents` 是否恰好 1 个。
- 是否没有额外手写“目录”标题，例如 `$\equiv$ 目录`。
- `\setcounter{tocdepth}{3}` 是否存在，保证三级标题进入目录。
- `\setcounter{secnumdepth}{0}` 是否存在，避免 LaTeX 自动编号和 Markdown 原始编号叠加。
- 正文标题是否使用普通 `\section{...}` / `\subsection{...}` / `\subsubsection{...}`，而不是大量 `\section* + \addcontentsline`。
- 标题数量是否和 Markdown 标题数量大致一致。
- 是否不存在“自动编号 + 源标题编号”叠加的双重编号风险。
- 页眉是否只使用 `\leftmark`，不能使用 `\thesection \leftmark`。
- 是否不存在 `0 目录` 风险。
- 公式中是否不存在 `\\_point`、`\\_hat` 这类会触发换行的双反斜杠变量。
- 是否不存在残留 Markdown 围栏 ```、Markdown TOC 锚点 `](#...)`、乱码 `�`。

### B. 编译核验（如果环境有 XeLaTeX）

必须至少编译两次：

```bash
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

然后检查：

- `.toc` 文件存在且非空。
- `.toc` 中 `\contentsline` 数量大于 0。
- PDF 文本中“目录”页后能看到章节标题，而不是只有一个“目录”。
- PDF 文本中没有 `0 目录` 页眉。
- PDF 文本中没有带下划线变量被错误拆成多行。

如果本地没有 XeLaTeX，必须在报告中明确写：`compile_verification: skipped_no_xelatex`，不能把静态检查说成完整通过。

## 目录与编号推荐策略

对于源 Markdown 已经自带编号的长文档，推荐：

```latex
\setcounter{tocdepth}{3}
\setcounter{secnumdepth}{0}
```

并使用普通标题命令：

```latex
\section{一级标题}
\subsection{二级标题}
\subsubsection{三级标题}
```

这样 LaTeX 不会额外打印自动编号，但普通标题仍会自动写入目录并更新页眉。不要大量使用 `\section* + \addcontentsline`，否则目录和页眉更容易失效。
