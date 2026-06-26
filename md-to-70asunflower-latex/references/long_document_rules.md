# 长篇技术手册转换规则

本规则面向几千行 Markdown、几十个章节、大量表格与代码块的技术文档。

## 1. 默认启用长文档模式

长文档默认在模板中启用：

```latex
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{makecell}
\usepackage{ragged2e}
\usepackage{xurl}
\usepackage{needspace}
\usepackage{placeins}
\usepackage{fvextra}
\usepackage{microtype}
\setcounter{tocdepth}{3}
\setcounter{secnumdepth}{0}
\linespread{1.08}
\emergencystretch=3em
\sloppy
```

## 2. 标题与分页

标题前建议加入：

```latex
\Needspace{6\baselineskip}
```

Part 级标题可使用 `partcard`：

```latex
\clearpage
\begin{partcard}
{\LARGE\bfseries\color{Primary} 源文档一级标题}
\end{partcard}
```

如果需要让 Part 进入目录，可额外写：

```latex
\addcontentsline{toc}{section}{源文档一级标题}
```

## 3. 标题层级建议

对于书籍式结构：

```text
# 篇章标题 / Chapter Title / Part Title       → partcard / section
## 二级标题       → section 或 subsection
### 三级标题     → subsection 或 subsubsection
#### 细分主题        → paragraph
```

转换器可根据文档结构选择：

- 若只有一个顶层 `# 标题`，跳过它作为封面标题。
- 后续 `# Part` 作为 Part 分隔。
- 编号章节 `## 1.` 作为主要章节。

## 4. 表格策略

| 表格类型 | 推荐策略 |
|---|---|
| 2-4 列短表格 | `tabularx` + `Y` 列 |
| 5-7 列表格 | `\small` 或 `\footnotesize` + `tabularx` |
| 很长多行表格 | `longtable` |
| 极宽表格 | 拆成多个表，或转为列表 |
| 含大量代码/路径 | 缩小字号并允许换行 |

默认优先使用：

```latex
\begin{center}
\small
\begin{tabularx}{\textwidth}{YYYY}
...
\end{tabularx}
\end{center}
\normalsize
```

## 5. 代码块策略

长代码块必须允许换行：

```latex
breaklines=true,
breakatwhitespace=false,
columns=fullflexible,
keepspaces=true
```

无语言代码块默认使用：

```latex
\begin{codebox}[Text]
\begin{lstlisting}
...
\end{lstlisting}
\end{codebox}
```

不要强行转换成公式。

## 6. 核心要点与面试常问

如果 Markdown 中出现：

```markdown
### 核心要点
- ...
```

可转换为：

```latex
\begin{keypointsbox}
\begin{itemize}
  \item ...
\end{itemize}
\end{keypointsbox}
```

如果出现：

```markdown
### 面试常问
**Q1：...**
```

可转换为：

```latex
\begin{interviewbox}
...
\end{interviewbox}
```

## 7. 目录策略

长文档目录不宜过深：

```latex
\setcounter{tocdepth}{3}
```

正文编号可以保留到三级：

```latex
\setcounter{secnumdepth}{0}
```

## 8. Overleaf 性能建议

- 长文优先单文件交付，必要时再拆分多文件。
- 图片资源放入 `assets/figures/`。
- 如果编译慢，先关闭水印或拆分章节定位问题。
- 使用 XeLaTeX 编译。

## 9. 长文编号策略

长文档若源 Markdown 已经自带章节编号，应保留源编号并禁用 LaTeX 自动编号。推荐做法是设置 `secnumdepth=0`，然后使用普通标题命令：

```latex
\setcounter{tocdepth}{3}
\setcounter{secnumdepth}{0}

\section{源文档一级标题}
\subsection{源文档二级标题}
\subsubsection{源文档三级标题}
```

普通标题会自动进入目录、自动更新页眉；`secnumdepth=0` 让 LaTeX 不再生成 `1.1.2` 之类自动编号，从而避免与源编号叠加。

> 不推荐用大量 `\section* + \phantomsection + \addcontentsline` 手写目录项。星号标题不会自动更新页眉 mark，也更容易出现目录/页眉不同步问题。

目录页码必须编译两次 XeLaTeX；第一次生成 `.toc`，第二次刷新页码。

## 10. 字体与公式排版

长篇技术文档应明确区分正文、中文、代码和公式字体：

- 正文英文/数字使用 Times-like 字体；
- 中文使用宋体/黑体 CJK 字体；
- 代码使用等宽字体；
- 数学表达式进入 `mathbox`，不要留在 `codebox[Text]`。

短公式 text block 应自动识别并转成数学公式，尤其是包含关系符、指数、乘法、函数调用、下划线变量等公式特征的片段。


## 11. 普适性要求

长文档规则只能描述结构模式，不能写死某篇文章的章节名、编号或术语。例如：

- 使用“篇章标题 / Chapter / Part / 模块标题”描述结构；
- 使用“自带编号标题”描述编号模式；
- 使用“带下划线变量名”描述公式变量模式；
- 使用“短公式 text block”描述公式识别模式。

不要把某一篇文章的章节名写死到规则里。
