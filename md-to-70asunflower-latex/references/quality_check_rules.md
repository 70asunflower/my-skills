# 质量检查规则

Markdown 转 LaTeX 后必须生成静态检查报告。即使当前环境没有 `xelatex`，也应完成这些检查。

## 1. 必查项目

- `\begin{...}` / `\end{...}` 是否配对
- 花括号 `{}` 是否平衡
- 是否残留 Markdown 代码围栏 ```
- 是否残留 Markdown 目录锚点 `](#...)`
- 是否残留 HTML `<br>`、`<div>` 等未处理标签
- 是否出现 `\begincodebox`、`\beginlstlisting` 这类拼接错误
- 是否出现乱码字符 `�`
- 是否有未闭合列表环境
- 是否有明显超宽表格风险
- 是否存在空标题

## 2. 推荐输出报告

生成：

```text
STATIC_CHECK_REPORT.txt
```

报告至少包含：

```text
Static LaTeX Check Report
==========================
File: main.tex
Lines: xxxx
Chars: xxxx
Environment errors: 0
Unclosed environments: 0
Brace balance: 0
Residual markdown fences: 0
Residual markdown toc anchors: 0
Replacement chars: 0
Tables: xx
Codeboxes: xx
Note: xelatex status ...
```

## 3. 本地编译策略

如果环境有 `xelatex`：

```bash
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

如果没有 `xelatex`：

1. 不要中断任务。
2. 完成静态检查。
3. 在 README 中说明：当前环境未安装 XeLaTeX，需上传 Overleaf 编译。
4. 输出 `.tex` 和项目压缩包。

## 4. 常见失败定位

| 现象 | 可能原因 | 修复 |
|---|---|---|
| `Missing $ inserted` | `_` 未转义或数学模式错误 | 普通文本转义 `_` |
| `Misplaced alignment tab character &` | `&` 未转义 | 转成 `\&` |
| `Environment ... undefined` | 模板环境未定义 | 检查模板是否包含对应 tcolorbox |
| `Runaway argument` | 花括号不平衡 | 查找最近的 `{}` 或命令参数 |
| `Package listings Error` | lstlisting 嵌套或语言问题 | 使用受支持语言或留空 |
| 表格超宽 | 列太多或内容太长 | 使用 `tabularx`、缩小字号或拆表 |

## 5. 人工抽查建议

对于长文档，除静态检查外，建议人工抽查：

- 封面标题、日期、作者、标签是否正确
- 摘要是否过长
- 目录是否重复
- Part 分隔是否清晰
- 表格是否过密
- 代码块是否被错误转义
- 核心要点/面试常问是否醒目


## 6. 目录与编号检查

必须检查：

- 是否只有一个 `\tableofcontents`，且没有额外手写的“目录”标题。
- 是否设置了 `\setcounter{secnumdepth}{0}`（源标题自带编号时），避免自动编号与源编号叠加。
- 正文标题是否使用普通 `\section{...}` / `\subsection{...}` / `\subsubsection{...}`；不推荐大量使用 `\section* + \addcontentsline`。
- 标题数量是否与源 Markdown 标题数量大致一致（覆盖率达标）。
- README 顶部是否有醒目提示「目录为空 = 只编译了一遍，必须编译两遍 XeLaTeX」。
- 项目是否随包附带 `compile.bat`、`compile.sh`、`latexmkrc`（从 skill `assets/` 复制）。

> 经验：用户反馈的“目录空白 / 页码全是 0 / 页码不对”几乎都是只跑了一遍 xelatex（或用了只跑一遍的一键编译工具/agent）。这不是 `.tex` 的 bug，不要改结构去“修”它；用 `compile.bat` / `compile.sh` / latexmk / texify 跑够遍数即可。

## 7. 页眉与公式检查

必须检查：

- 页眉模板是否为 `\leftmark`，不要包含 `\thesection \leftmark`。
- 是否不存在 `0 目录` 这种页眉风险。
- 如果确实使用了星号标题 `\section*`，是否显式调用了 `\markboth{...}{}`（普通标题由模板自动处理，无需）。
- 公式中是否不存在 `\\_point`、`\\_hat` 这类会触发换行的双反斜杠下划线。
- 带下划线的文本变量是否为 `\mathrm{identifier\_name}` 形式。

## 8. 转换质量核验不等于编译不报错

必须区分：

- LaTeX 语法检查：环境配对、花括号平衡、无非法命令。
- 转换结构检查：目录、标题层级、页眉、列表、公式是否符合预期。
- PDF 视觉检查：目录是否真的有内容、页眉是否正确、公式是否断裂。

最低核验指标：

```text
tableofcontents_count == 1
manual_toc_heading_count == 0
tocdepth == 3
secnumdepth == 0
heading_count_tex >= heading_count_markdown * 0.95
bad_header_thesection_leftmark == false
bad_formula_double_backslash_underscore == false
residual_markdown_fence == 0
compile_helpers_present == true   # compile.bat / compile.sh / latexmkrc
readme_two_pass_warning == true
```

如果有 XeLaTeX，还必须检查 `.toc` 文件：

```text
toc_file_exists == true
toc_contentsline_count > 0
```

并用 `pdftotext` 抽查 PDF：目录页不能只有“目录”两个字。


## 9. 普适核验原则

检查项必须是模式化的，不能依赖某一篇文章的具体标题或具体变量名。推荐检查：

- 是否存在自动编号与源标题编号叠加的模式；
- 是否存在带下划线变量被双反斜杠错误转义的模式；
- 是否存在目录为空、目录重复、页眉停留在目录页的模式；
- 标题覆盖率是否达标；
- 公式框、代码框、表格、列表的数量是否与源文档结构大致匹配。
