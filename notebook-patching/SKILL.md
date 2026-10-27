---
name: notebook-patching
description: Jupyter Notebook (.ipynb) 与 IDE 打开状态下的结构化文件快速安全修改工作流。规避内置编辑工具对 ipynb 的限制、避开 Windows PowerShell/Cmd 内联转义与 GBK 编码陷阱、解决 VS Code Notebook 内存缓冲区与 Auto-Save 覆盖冲突。包含一击必中的 Python 补丁脚本标准范式与交付重载指引。
---

# notebook-patching：Jupyter Notebook 与受限文件安全修改指南

在 AI Agent 辅助编程中，修改 `.ipynb`（Jupyter Notebook）经常遭遇“修改极慢”、“反复报错报错”、“改了却像没改一样”的困境。本技能总结了核心根因与标准化高效率路径。

---

## 一、为什么传统修改方式极慢？（核心瓶颈与痛点）

1. **工具层硬性限制（Tool Boundary）**
   - 多数 Agent IDE 的文本局部替换工具（如 `replace_file_content`）明确禁止直接编辑 `.ipynb` 文件（防止正则表达式破坏复杂的 JSON 树状结构），迫使 Agent 退化到命令行执行。
2. **Windows Shell 转义与编码陷阱（The Syntax & Encoding Trap）**
   - 试图在终端里执行单行命令 `python -c "..."` 时，频繁遇到：
     - **引号解析冲突**：PowerShell / Cmd 解析双引号嵌套导致 `SyntaxError: unterminated string literal`；
     - **PowerShell 变量吞噬**：PowerShell 会自动将 `$var` 视为自身变量求值，导致 Python 脚本接收到空字符串；
     - **GBK 默认编码报错**：Windows 控制台默认代码页非 UTF-8，当 Notebook 包含 Emoji 或中文排版符号时，直接抛出 `UnicodeEncodeError`；
     - 以上问题通常导致 Agent 试错 2~4 轮，造成严重的时间与 Token 浪费。
3. **IDE 内存编辑器与磁盘覆盖冲突（The In-Memory Buffer Revert）——最隐蔽的静默回滚**
   - 用户在 IDE（如 VS Code）中通常正处于该 Notebook 的可视化编辑界面，甚至光标正聚焦在目标单元格中；
   - 当外部脚本把修改写入磁盘上的 `.ipynb` 后，VS Code 的 Notebook 内核**不会静默热重载**已聚焦或处于编辑态的单元格；
   - 随之而来的 **Auto-Save（自动保存）** 或用户切换窗口引发的失焦保存，会把 IDE 内存中的旧版本重新写回磁盘，瞬间覆盖外部修改，呈现“文件内容根本没改”的假象。

---

## 二、黄金避坑五原则

- **原则 1：通过文件写入工具写至系统临时目录，严禁终端内联拼接（No Inline One-Liners）**
  - 永远不要用 `python -c "..."` 或在 PowerShell 里拼接复杂的多行 Python。
  - **最佳范式**：直接使用 Agent 的原生文件写入工具（如 `write_to_file`）将独立补丁脚本写至系统临时目录（如 Windows 的 `C:/Users/<User>/AppData/Local/Temp/patch_xxx.py` 或 `$env:TEMP`）。这完全绕过 Shell 解释器，彻底杜绝引号转义、编码乱码与长字符串截断。
  - **绝不在 IDE 中打开临时文件（IDE 零弹窗规约）**：中间过程补丁写在系统临时目录，执行后立即调用删除命令清理，绝不污染项目工作区。注意：部分 IDE 环境会监听文件生成事件并在标签页弹出该文件，执行完毕后若发现残留标签必须提醒用户仅关注目标 notebook，不要保存临时文件，保持 IDE 极简干净。
- **原则 2：警惕 LaTeX 与数学符号的 Shell 变量吞噬（The $Q, $K, $V Trap）**
  当 Notebook 单元格包含学术公式或符号（如 `$Q$`, `$K$`, `$V$`, `$B$`, `$T$`, `\lim`）时，若在终端直接传递，PowerShell 会将以 `$` 开头的数学记号误当成自身变量求值，静默替换为空值或抛出 `MissingArgument` 语法错误。通过原生文件工具写入临时 `.py` 脚本是避开此陷阱的唯一正解。
- **原则 3：显式强制 UTF-8 运行环境**
  在 Windows 下执行 Python 补丁时，统一使用 `cmd /c "set PYTHONIOENCODING=utf-8 && python ..."` 或 `python -X utf8 script.py`，彻底消灭 Windows 控制台默认 GBK 编码导致的 `UnicodeEncodeError`。
- **原则 4：严格遵循 Notebook JSON 格式规范**
  - 读取与写入均使用 `encoding="utf-8"`；
  - 缩进保持一致（通常为 `indent=1`，紧凑型 VS Code 标准）；
  - `cells[i]["source"]` 必须维持每一行均以 `\n` 结尾的字符串列表（List of Strings），确保在 Git Diff 和 Notebook 渲染器中换行正确；
  - `json.dump(..., ensure_ascii=False, indent=1)`。
- **原则 5：IDE 缓冲区刷新提醒与交付防覆盖（The Stale Cache & Revert Rule）**
  - 外部脚本修改磁盘后，VS Code / Antigravity IDE 对已打开且处于激活态的 `.ipynb` 或 SVG 图表**不会静默热重载**，甚至可能被 IDE 的 Auto-Save（自动保存）反向冲刷覆盖。
  - 交付后必须明确提醒用户：**只刷新/还原最主要的 notebook 文件**，按 `Ctrl+Shift+P` 执行 `File: Revert File`（还原文件）或重新打开该 notebook 文件标签页，确保 IDE 加载磁盘最新内容。
- **原则 6：关联架构图排版安全与 snap 无头视觉门禁（SVG Anti-Overlap Gate）**
  - **局部坐标隔离**：卡片内部的数值面板、状态块必须使用独立 `<g transform="translate(x, y)">` 子容器隔离局部坐标系，杜绝局部小 `y` 坐标逃逸回父级导致文字层叠；
  - **文本行宽预算**：SVG `<text>` 不会自适应换行，长文本必须按容器宽度与字号精算拆分为多行（垂直步长 $16\sim22\text{px}$）；
  - **强制无头渲染审查**：严禁仅通过 XML 语法检查就交付，必须调用 `snap` CLI 渲染高清 PNG，并使用 `view_file` 亲自审查文字排版无重叠无粘连。

---

## 三、标准化操作流水线（Standard Workflow）

### 步骤 1：定位目标单元格
通过只读工具或精简脚本找到目标 Cell 索引（避免盲猜索引）：

```python
import json

path = r"path/to/notebook.ipynb"
with open(path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for idx, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    header = src.strip().split("\n")[0] if src.strip() else "(empty)"
    print(f"Cell {idx:2d} [{cell['cell_type']}]: {header[:60]}")
```

### 步骤 2：生成并执行系统临时 Patch 脚本
直接用文件写入工具在 `$env:TEMP` 写入独立的补丁脚本（如 `C:/Users/<User>/AppData/Local/Temp/patch_nb.py`），绝不放入工作区，绝不在 IDE 中打开：

```python
import json

path = r"exercises/ch02/07_kv_cache_principle.ipynb"

with open(path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 目标单元格索引与替换
target_cell_idx = 1
new_content = """## 🎯 学习目标
- 点 1：规范简洁表述
- 点 2：明确核心概念
"""

# 转换为 Notebook 标准的以 \n 结尾的字符串列表
lines = [line + "\n" for line in new_content.split("\n")]
if lines and not new_content.endswith("\n"):
    lines[-1] = lines[-1][:-1]

nb["cells"][target_cell_idx]["source"] = lines

with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")

print("Notebook cell updated successfully.")
```

在终端执行：
```powershell
python $env:TEMP\patch_nb.py; Remove-Item $env:TEMP\patch_nb.py
```

### 步骤 3：无阻塞语法验证（Headless Validation）
对于含有交互绘图（如 Plotly `fig.show()`）的代码单元格，严禁在无头终端中完整执行，否则 Plotly 会尝试启动本地浏览器服务器导致终端持续阻塞。
**最佳验证方式**：使用静态语法编译瞬时校验所有代码单元格：
```python
import json

with open("path/to/notebook.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        compile("".join(cell["source"]), f"cell_{i}", "exec")
print("All code cells syntax valid.")
```

### 步骤 4：轻量通知与刷新指引
落盘后向用户确认修改完成，简要列出核心改动点，并主动提醒刷新：
> “修改已写入磁盘（核心改动：...）。由于 IDE 打开文件存在内存缓存，若你当前正打开该文件，请按 `Ctrl+Shift+P` 执行 `File: Revert File` 或重新打开该标签页，以加载磁盘最新版本。”
> （注：严禁在回复中把刚修改的长文本/代码再重复贴一遍）。
