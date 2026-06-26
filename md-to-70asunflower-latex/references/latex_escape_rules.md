# LaTeX 特殊字符转义规则

Markdown 转 LaTeX 时，最容易出错的是普通文本中的 LaTeX 特殊字符。转换器必须区分普通文本、表格、行内代码、代码块和公式块。

## 1. 必须转义的字符

普通文本和表格单元格中必须转义：

| 字符 | 转义结果 |
|---|---|
| `\` | `\textbackslash{}` |
| `&` | `\&` |
| `%` | `\%` |
| `$` | `\$` |
| `#` | `\#` |
| `_` | `\_` |
| `{` | `\{` |
| `}` | `\}` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |

## 2. 场景差异

| 场景 | 是否转义 | 说明 |
|---|---|---|
| 普通正文 | 必须转义 | 防止 LaTeX 编译失败 |
| 表格单元格 | 必须转义 | 特别注意 `&`、`_`、`%` |
| 行内代码 | 先转义，再放入 `\codeinline{}` | 不建议直接用 `\verb` |
| 代码块 | 不转义 | 放入 `lstlisting`，保持原样 |
| 公式块 | 不按普通文本转义 | 保留 LaTeX 数学语法 |
| URL | 使用 `\url{}` 或转义后普通展示 | 推荐配合 `xurl` |

## 3. 行内 Markdown 处理顺序

推荐顺序：

1. 先识别行内代码 `` `...` ``，暂存内容。
2. 识别行内公式 `$...$`，暂存内容。
3. 识别粗体、斜体、高亮。
4. 对剩余普通文本执行 LaTeX 转义。
5. 将暂存的代码/公式/命令放回。

这样可以避免把 LaTeX 命令本身再次转义。

## 4. 代码块原则

`lstlisting` 内部不要做 LaTeX 转义。例如：

```latex
\begin{codebox}[Python]
\begin{lstlisting}[language=Python]
def f(x_y):
    return x_y * 100  # 这里的 _ 和 # 不需要转义
\end{lstlisting}
\end{codebox}
```

## 5. 公式块原则

公式块应保留 LaTeX 数学语法，例如：

```latex
\begin{mathbox}
\[
Y = S_x S_w \cdot (X_{int8} W_{int8})
\]
\end{mathbox}
```

不要把公式中的 `_` 转成 `\_`。

## 6. 常见错误

| 错误 | 原因 | 修复 |
|---|---|---|
| `Missing $ inserted` | 普通文本含 `_` 未转义 | `\_` |
| `Misplaced alignment tab character &` | 普通文本或表格单元格含 `&` 未转义 | `\&` |
| `Runaway argument` | 花括号不平衡 | 检查 `{}` |
| `Undefined control sequence` | 反斜杠被误当命令 | 普通文本中转成 `\textbackslash{}` |
| 表格列错乱 | 单元格里的 `|` 或 `&` 未处理 | 转义或合并单元格内容 |
