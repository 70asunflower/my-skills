# Markdown → 70asunflower LaTeX 转换规则 v2

## 1. 标题映射

### short_blog 模式

| Markdown | LaTeX |
|---|---|
| `# 一级标题` | `\section{一级标题}` |
| `## 二级标题` | `\subsection{二级标题}` |
| `### 三级标题` | `\subsubsection{三级标题}` |
| `#### 四级标题` | `\paragraph{四级标题}\mbox{}\\` |

### long_technical_manual 模式

| Markdown | LaTeX 建议 |
|---|---|
| `# 篇章 / Chapter / Part 标题` | `partcard` 分隔块，或 `\section{原标题}` |
| `# 一级标题` | `\section{原标题}` |
| `## 二级标题` | `\subsection{原标题}` |
| `### 三级标题` | `\subsubsection{原标题}` |
| `#### 更小标题` | `\paragraph{更小标题}\mbox{}\\` |

标题前建议加入：

```latex
\Needspace{6\baselineskip}
```

避免标题出现在页面底部。

## 2. Markdown 手写目录

默认跳过以下结构：

```markdown
## 目录
- [xxx](#xxx)
...
---
```

LaTeX 中使用：

```latex
\tableofcontents
```

## 3. 公式

| Markdown | LaTeX |
|---|---|
| `$E=mc^2$` | 直接保留为行内公式 |
| `$$...$$` | `mathbox` + `\[...\]` |

独立公式：

```latex
\begin{mathbox}
\[
E=mc^2
\]
\end{mathbox}
```

无语言代码块不要自动转公式，除非确认内容是合法 LaTeX 数学表达。

## 4. 代码块

Markdown：

````markdown
```python
def hello():
    pass
```
````

LaTeX：

```latex
\begin{codebox}[Python]
\begin{lstlisting}[language=Python]
def hello():
    pass
\end{lstlisting}
\end{codebox}
```

### 语言映射

| Markdown | codebox 标题 | listings language |
|---|---|---|
| `python`, `py` | Python | Python |
| `bash`, `shell`, `sh` | Bash | bash |
| `javascript`, `js` | JavaScript | JavaScript |
| `typescript`, `ts` | TypeScript | JavaScript |
| `cpp`, `c++` | C++ | C++ |
| `c` | C | C |
| `cuda`, `cu` | CUDA | C++ |
| `tex`, `latex` | LaTeX | TeX |
| `json` | JSON | 留空或自定义 |
| `yaml`, `yml` | YAML | 留空或自定义 |
| `toml` | TOML | 留空或自定义 |
| `sql` | SQL | SQL |
| `markdown`, `md` | Markdown | 留空 |
| `text`, `plaintext`, 无语言 | Text | 留空 |

## 5. 引用块与 callout

| Markdown | LaTeX |
|---|---|
| `> 普通引用` | `quotebox` |
| `> **提示**：...` | `tipbox` |
| `> **注意**：...` | `warnbox` |
| `> **警告**：...` | `warnbox` |
| `> **核心结论**：...` | `tipbox` 或 `quotebox` |
| `> **面试重点**：...` | `interviewbox` |
| `[!NOTE]` | `tipbox` |
| `[!TIP]` | `tipbox` |
| `[!WARNING]` | `warnbox` |
| `[!IMPORTANT]` | `quotebox` 或 `tipbox` |

## 6. 列表

无序列表：

```latex
\begin{itemize}
  \item 项目一
  \item 项目二
\end{itemize}
```

有序列表：

```latex
\begin{enumerate}
  \item 步骤一
  \item 步骤二
\end{enumerate}
```

Markdown 任务列表（checkbox）应放在 `itemize` 环境里，用 `\item[符号]` 显示勾选状态，符号映射统一为：

- 未勾选 `- [ ] xxx` → `\item[$\square$] xxx`
- 已勾选 `- [x] xxx`（`x` 大小写均可） → `\item[$\boxtimes$] xxx`

完整示例（与转换器输出一致）：

```latex
\begin{itemize}
  \item[$\square$] 未完成的任务
  \item[$\boxtimes$] 已完成的任务
\end{itemize}
```

注意：`$\square$` / `$\boxtimes$` 是 LaTeX 内置数学符号，无需在模板里额外定义；不要写成裸符号或普通 `\item`，否则勾选框不会显示。

## 7. 表格

短表格也建议默认使用 `tabularx`：

```latex
\begin{center}
\small
\begin{tabularx}{\textwidth}{YYY}
\toprule
\textbf{列1} & \textbf{列2} & \textbf{列3} \\
\midrule
A & B & C \\
\bottomrule
\end{tabularx}
\end{center}
\normalsize
```

列类型 `Y` 在模板中定义为：

```latex
\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}
```

## 8. 文本高亮

| Markdown | LaTeX | 用途 |
|---|---|---|
| `**关键词**` | `\keyword{关键词}` | 关键结论或术语 |
| `*概念*` | `\concept{概念}` | 概念强调 |
| `==高亮==` | `\highlight{高亮}` | 背景高亮 |
| `` `代码` `` | `\codeinline{代码}` | 行内代码 |
| FP16 / INT8 等 | `\dtype{FP16}` | 可选，数据类型 |
| GPTQ / AWQ 等 | `\method{GPTQ}` | 可选，方法名 |

注意：不要全文过度高亮，优先用于标题、表格、关键句。

## 9. 封面元信息布局

封面 logo、日期、作者、标签必须分行显示，避免视觉拥挤：

```latex
\sunflowerwatermark[100]{2.5}\par
\vspace{0.45cm}
{\small\color{gray!70}$\bullet$ 2026年6月}\par
\vspace{0.12cm}
{\small\color{gray!70}$\bullet$ 70asunflower}\par
\vspace{0.12cm}
{\small\color{gray!70}$\bullet$ AI Infra, LLM 推理, CUDA}\par
```

结尾页脚只保留“70asunflower / 感谢阅读，欢迎交流”。


## 10. 目录与双重编号处理

LaTeX 的 `\tableofcontents` 会自动生成“目录”标题。不要在 `\tableofcontents` 前再手写一个“目录”标题，否则会出现两个“目录”。

如果 Markdown 标题已经自带编号，例如：

```markdown
### 源文档三级标题
### 另一个源文档三级标题
```

**推荐做法**：使用 `\setcounter{secnumdepth}{0}` 关闭 LaTeX 自动编号，然后照常使用普通标题命令：

```latex
\setcounter{secnumdepth}{0}

\subsubsection{源文档三级标题}
\subsubsection{另一个源文档三级标题}
```

这样：

- 普通标题会自动进入目录、自动更新页眉；
- `secnumdepth=0` 保证 LaTeX 不再额外打印自动编号；
- Markdown 原标题中的编号（如 `6.2`）完整保留。

如果不做这一步，直接用默认 `secnumdepth` 的普通标题，PDF 会出现“自动编号 + 源编号”叠加：

```text
4.1.2 源文档三级标题
5.1.5 另一个源文档三级标题
```

> 不推荐用大量 `\section* + \addcontentsline` 手写目录来避免双重编号。那种做法在长文档中更容易导致目录为空、页眉停留在“目录”等问题。`secnumdepth=0 + 普通标题` 是首选。

## 11. 无语言代码块的公式识别

无语言 / `text` 代码块分两类：

1. 说明性文本、流程图、含中文内容：继续使用 `codebox[Text]`。
2. 短数学表达式：转换为 `mathbox`。

公式识别应保守，同时满足以下全部条件才转 `mathbox`（宁可漏转，不要误转）：

1. 行数不超过 8 行；
2. 不含中文；
3. 包含 `=`、`≈`、`≤`、`≥` 等关系符；
4. **除关系符外，至少还含一个真正的数学运算**：运算符 `^`、`×`、`·`、`√`、`∑`、`*`、`+`、`/`、减号（`a - b` 或负号 `-127`），或数学函数 `round`/`clamp`/`sqrt`/`sum`/`min`/`max` 等；仅有 `key = value` 这类纯赋值不算。

即使上述条件满足，出现以下**非数学信号**时仍保留为代码框：

- Shell / 命令行：某行首个词是 `export`、`cd`、`pip`、`npm`、`git`、`docker`、`kubectl`、`make`、`python`、`bash` 等命令；或出现 `--`、`$(`、`${`、`&&`、`||`、`;`、`#!/`。
- 路径 / URL：出现形如 `/usr/bin/` 的路径片段或 `://`。
- JSON / 引号字符串：出现双引号 `"`（如 `{ "ttl": 60 }`）。
- 编程 / 流程符号：`->`、`=>`、`==`、`!=`、`<-`。
- 伪代码 / 纯赋值：`key = value`、`lr = 0.001`、`loss = model(x)`、`y = f(x)`（无真正数学运算）。

注意：逗号 `,`、冒号 `:`、方括号 `[ ]`、撇号 `'` 是合法数学写法（如 `clamp(x, a, b)`、`Y[:, j]`、`y'`），**不要**因为这些符号就拒转公式。

反例对比（应转公式）：`E = m c^2`、`scale = (max - min) / 255`、`q = clamp(round(x / scale) + zero\_point, qmin, qmax)`、`y' = gamma × (y - mean) / sqrt(var + eps)`；（应保留代码）：`export PATH=/usr/bin`、`{ "ttl": 60 }`、`redis-cli --scan`。

示例：

```text
value = (-1)^sign × mantissa × 2^exponent
```

转换为：

```latex
\begin{mathbox}
\[
\begin{aligned}
\mathrm{value} &= (-1)^{\mathrm{sign}} \times \mathrm{mantissa} \times 2^{\mathrm{exponent}}
\end{aligned}
\]
\end{mathbox}
```


## 12. 页眉与公式下划线修复规则

**页眉**：推荐使用普通标题命令 `\section{...}`。模板已通过 `\sectionmark` 自动更新页眉，无需手动 `\markboth`。只有在不得不使用星号标题 `\section*{...}` 时，才需要在标题后手动补一句：

```latex
\markboth{当前章节标题}{}
```

模板页眉不要使用 `\thesection \leftmark`，应使用 `\fancyhead[R]{\small\color{Primary}\leftmark}`，否则可能出现 `0 目录` 页眉。

**公式下划线**：数学公式中的下划线变量应使用单反斜杠转义，例如：

```latex
\mathrm{identifier\_name}
```

禁止生成 `\mathrm{identifier\\_name}`，因为 `\\` 会在数学环境中触发换行，把变量名拆成两行。

## 13. 推荐目录生成策略：secnumdepth=0 + 普通标题

对于 Markdown 标题自带编号的技术手册，不要用 LaTeX 自动编号，也不要大量使用星号标题手写目录。推荐：

```latex
\setcounter{tocdepth}{3}
\setcounter{secnumdepth}{0}

\section{源文档一级标题}
\subsection{源文档二级标题}
\subsubsection{源文档三级标题}
```

这样：

- PDF 正文不会显示额外的 LaTeX 编号；
- 标题原始编号仍保留；
- `\tableofcontents` 能自动收集目录项；
- 页眉 mark 能正常更新。

转换后必须核验 `.tex` 中 `\tableofcontents` 为 1 个、`tocdepth=3`、`secnumdepth=0`、标题命令数量与源 Markdown 匹配。


## 14. 普适性要求

转换规则不能依赖某一篇文章的固定标题、固定章节号或固定术语。应根据结构和模式判断：

- “源标题是否自带编号”是模式，不是某个具体编号。
- “带下划线的变量名”是模式，不是某个具体变量。
- “篇章标题 / Chapter / Part / 模块标题”是结构，不是某个固定 Part 名称。
- 公式识别应依据关系符、指数、乘法、函数调用、下划线变量等通用数学特征。

规则必须基于标题结构，而不是基于某篇文章的固定标题。
