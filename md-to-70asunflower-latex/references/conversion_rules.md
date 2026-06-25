# Markdown → 70asunflower LaTeX 转换规则速查表

## 章节标题

| Markdown | LaTeX |
|---------|-------|
| `# 一级标题` | `\section{一级标题}` |
| `## 二级标题` | `\subsection{二级标题}` |
| `### 三级标题` | `\subsubsection{三级标题}` |

## 公式

| Markdown | LaTeX |
|---------|-------|
| `$E=mc^2$` | `$E=mc^2$`（直接保留） |
| `$$E=mc^2$$` | `\begin{mathbox}\[ E=mc^2 \]\end{mathbox}` |

## 代码块

| Markdown | LaTeX |
|---------|-------|
| ` ```python ` | `\begin{codebox}[Python]\begin{lstlisting}[language=Python]...\end{lstlisting}\end{codebox}` |
| ` ```bash ` | `\begin{codebox}[Bash]...` |
| ` ```javascript ` | `\begin{codebox}[JavaScript]...` |
| ` ```cpp ` | `\begin{codebox}[C++]...` |
| ` ```tex ` | `\begin{codebox}[LaTeX]...` |
| 其他语言 | `\begin{codebox}[Code]...` |

## 引用块

| Markdown | LaTeX |
|---------|-------|
| `> 普通引用` | `\begin{quotebox}...\end{quotebox}` |
| `> **提示**：...` | `\begin{tipbox}\textbf{$\rightarrow$ 提示：}...\end{tipbox}` |
| `> **注意**：...` | `\begin{warnbox}\textbf{$\triangle$ 注意：}...\end{warnbox}` |
| `> **警告**：...` | `\begin{warnbox}\textbf{$\triangle$ 警告：}...\end{warnbox}` |

## 列表

| Markdown | LaTeX |
|---------|-------|
| `- 项目` | `\item 项目`（在 `itemize` 内） |
| `1. 步骤` | `\item 步骤`（在 `enumerate` 内） |

## 文本高亮

| Markdown | LaTeX | 效果 |
|---------|-------|------|
| `**关键词**` | `\keyword{关键词}` | 蓝色粗体 |
| `*概念*` | `\concept{概念}` | 紫色粗体 |
| `==高亮==` | `\highlight{高亮}` | 橙色背景 |
| `` `代码` `` | `\codeinline{代码}` | 等宽字体 |

## 封面占位符

| 内容 | Markdown 来源 | LaTeX 位置 |
|------|--------------|------------|
| 标题 | `# 标题` 或 YAML `title` | `\begin{covercard} {\Huge... 标题} ...` |
| 副标题 | 首段或 YAML `subtitle` | `{\Large\color{Primary!80} 副标题}` |
| 日期 | YAML `date` | `$\bullet$ 日期` |
| 作者 | YAML `author` | `$\bullet$ 作者` |
| 标签 | YAML `tags` | `$\bullet$ 标签1, 标签2` |
| 摘要 | YAML `abstract` | `\begin{abstractcard}...\end{abstractcard}` |

## 编译说明

1. 上传 `.tex` 文件到 Overleaf
2. Menu → Compiler → **XeLaTeX**
3. 点击 Recompile

## 注意事项

- **禁止**在 `codebox` 内使用 `verbatim`，必须用 `lstlisting`
- **禁止**使用 `fontawesome5`，已替换为数学符号
- 公式框内必须用 `\[...\]` 包裹
- 目录由 `\tableofcontents` 自动生成
