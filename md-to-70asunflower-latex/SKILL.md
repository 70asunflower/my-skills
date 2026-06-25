---
name: md-to-70asunflower-latex
description: 将 Markdown 技术博客转换为 70asunflower 风格的 LaTeX 文档（适配 Overleaf XeLaTeX 编译）。当用户需要将 Markdown 文章转为精美 PDF、生成技术博客 LaTeX 模板、或提到"70asunflower博客模板"时触发。
---

# Markdown 转 70asunflower LaTeX 博客模板

## 概述

本 Skill 将 Markdown 格式的技术博客内容转换为 70asunflower 个人品牌风格的 LaTeX 文档。转换后的 `.tex` 文件可直接在 **Overleaf** 上使用 **XeLaTeX** 编译器生成 PDF。

## 触发条件

当用户有以下需求时激活本 Skill：

- "把我的 Markdown 转成 LaTeX 博客"
- "用 70asunflower 模板生成 PDF"
- "Markdown 转 PDF"
- 提到"博客模板"、"技术笔记排版"
- 上传 `.md` 文件要求转换

## 文件结构说明

使用本 Skill 需要以下文件：

```
md-to-70asunflower-latex/
├── SKILL.md                          # 本文件（转换规则）
├── assets/
│   └── 70asunflower_blog_template.tex # LaTeX 模板文件
└── references/
    └── conversion_rules.md           # 详细转换规则参考
```

### 必需文件

| 文件 | 用途 | 放置位置 |
|------|------|----------|
| `SKILL.md` | Skill 主文件，包含转换指令 | Skill 根目录 |
| `70asunflower_blog_template.tex` | LaTeX 模板（Preamble + 示例） | `assets/` |
| `conversion_rules.md` | 详细元素映射表 | `references/` |

### 模板文件说明

`assets/70asunflower_blog_template.tex` 包含：

1. **Preamble（导言区）**：所有包、配色、页眉页脚、框体定义
2. **水印命令**：`\sunflowerwatermark`（纯 TikZ 绘制）
3. **自定义命令**：`\keyword`、`</code>、`</code>、`</code>`
4. **框体环境**：`covercard`、`abstractcard`、`mathbox`、`codebox`、`tipbox`、`warnbox`、`quotebox`
5. **封面示例**：展示标题、副标题、日期、作者、标签、摘要的填写位置

## 转换流程

### Step 1：读取用户 Markdown

提取以下信息：

```yaml
# YAML Frontmatter（如有）
title: "文章标题"
subtitle: "副标题（可选）"
date: "2026年6月"
author: "70asunflower"
tags: ["深度学习", "大模型"]
abstract: "摘要内容"
```

### Step 2：填充封面

替换模板中的占位符：

| 模板位置 | Markdown 来源 | LaTeX 代码 |
|---------|--------------|-----------|
| 大标题 | `title` 或第一个 `#` | `{\Huge\bfseries\color{Primary} 标题}` |
| 副标题 | `subtitle` 或首段描述 | `{\Large\color{Primary!80} 副标题}` |
| 日期 | `date` 或当前日期 | `$\bullet$ 2026年6月` |
| 作者 | `author` | `$\bullet$ 70asunflower` |
| 标签 | `tags` | `$\bullet$ 标签1, 标签2` |
| 摘要 | `abstract` 或第一段 | `\begin{abstractcard}...\end{abstractcard}` |

### Step 3：转换正文元素

#### 3.1 章节标题

```markdown
# 一级标题      →  \section{一级标题}
## 二级标题     →  \subsection{二级标题}
### 三级标题    →  \subsubsection{三级标题}
```

#### 3.2 公式

```markdown
行内：$E=mc^2$     →  直接保留 $E=mc^2$

独立：
$$E=mc^2$$         →  \begin{mathbox}
                      \[
                      E=mc^2
                      \]
                      \end{mathbox}
```

#### 3.3 代码块

```markdown
```python
def hello():
    pass
```               →  \begin{codebox}[Python]
                      \begin{lstlisting}[language=Python]
                      def hello():
                          pass
                      \end{lstlisting}
                      \end{codebox}
```

**语言标签映射**：

| Markdown | codebox 标题 |
|---------|-------------|
| `python` | `[Python]` |
| `bash` / `shell` | `[Bash]` |
| `javascript` / `js` | `[JavaScript]` |
| `cpp` / `c++` | `[C++]` |
| `tex` / `latex` | `[LaTeX]` |
| 其他 | `[Code]` |

#### 3.4 引用块

```markdown
> 普通引用        →  \begin{quotebox}...\end{quotebox}

> **提示**：...   →  \begin{tipbox}
                      \textbf{$\rightarrow$ 提示：}...
                      \end{tipbox}

> **注意/警告**：... →  \begin{warnbox}
                        \textbf{$\triangle$ 注意：}...
                        \end{warnbox}
```

#### 3.5 列表

```markdown
- 项目1          →  \begin{itemize}
- 项目2             \item 项目1
- 项目3             \item 项目2
                    \item 项目3
                    \end{itemize}

1. 步骤1         →  \begin{enumerate}
2. 步骤2            \item 步骤1
3. 步骤3            \item 步骤2
                    \item 步骤3
                    \end{enumerate}
```

#### 3.6 表格

```markdown
| 列1 | 列2 |
|-----|-----|
| A   | B   |   →  \begin{center}
                    \begin{tabular}{ll}
                    \toprule
                    \textbf{列1} & \textbf{列2} \
                    \midrule
                    A & B \
                    \bottomrule
                    \end{tabular}
                    \end{center}
```

#### 3.7 文本高亮

```markdown
**关键词**       →  \keyword{关键词}      （蓝色粗体）
*概念*           →  \concept{概念}        （紫色粗体）
==高亮==         →  \highlight{高亮}      （橙色背景）
`代码`           →  \codeinline{代码}     （等宽字体）
```

### Step 4：生成结语

如果 Markdown 有结尾段落，放入 `quotebox`；否则使用默认结语：

```latex
\section*{结语}
\begin{quotebox}
[用户Markdown的最后一段，或默认文本]
\end{quotebox}

\vspace{1cm}
\begin{center}
{\sunflowerwatermark[80]{1.5}}
\vspace{0.3cm}
\textcolor{gray!60}{\small$\star$ 70asunflower \quad $\heartsuit$ 感谢阅读，欢迎交流 \quad $\star$ 全网同名}
\end{center}
```

## 输出格式

最终生成一个完整的 `.tex` 文件，结构如下：

```latex
% 导言区（复制自模板，无需修改）
\documentclass[fontset=fandol,11pt,a4paper]{ctexart}
\usepackage{xeCJK}
\xeCJKsetup{AutoFakeBold=true, AutoFakeSlant=true}
% ... 所有包和定义 ...

\begin{document}
% 封面（填充用户内容）
% 目录（自动生成）
% 正文（转换后的内容）
% 结语
\end{document}
```

## 编译说明

告诉用户在 Overleaf 上：

1. 上传生成的 `.tex` 文件
2. 点击 **Menu** → **Compiler** → 选择 **XeLaTeX**
3. 点击 **Recompile**

## 注意事项

- **不要**在 `codebox` 内使用 `verbatim`，必须用 `lstlisting`
- **不要**使用 `fontawesome5` 图标，已替换为数学符号（`$\star$` `$\bullet$` 等）
- 公式框 `mathbox` 内的内容必须用 `\[...\]` 或 `$$...$$` 包裹
- 目录由 `\tableofcontents` 自动生成，无需手动维护
