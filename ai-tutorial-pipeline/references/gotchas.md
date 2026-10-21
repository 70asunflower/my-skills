# gotchas：实测踩坑实录（2026-08-29 电源设计教程实战）

每条都是真实故障 + 已验证的对策。对应逻辑已内置在 scripts/ 里，此处用于故障定位。

## 浏览器控制

### G1. Windows shell 内联中文 JSON 必坏
**症状**：curl -d '{"data":"中文"}' 到达守护进程变成 `???`。
**原因**：Windows 控制台编码（GBK/UTF-8 混杂）。
**对策**：所有含中文的请求用 Python urllib（`wb.py` 已封装）或写文件后 `--data-binary @file`。永远不内联。

### G2. WebBridge 的 `fill` 在千问输入框上必失败
**症状**：`fill: Uncaught`（扩展注入脚本报错）。
**原因**：千问输入框是 React 受控 `<textarea>`，非 contenteditable，fill 的事件序列不被接受。
**对策**：CDP 真实点击输入框聚焦 → `Input.insertText`（受信任输入事件，React 正常响应）→ 快照验证回显 → 点 Send 引用。已封装在 `wb.send_prompt()`。

### G3. 合成 click() 点复制按钮不写剪贴板
**症状**：`el.click()` 成功但剪贴板没内容。
**原因**：合成事件无 user activation，`navigator.clipboard.writeText` 被拒绝。
**对策**：必须 CDP `Input.dispatchMouseEvent`（受信任点击）。已封装在 `wb.capture_latest()`。

### G4. 系统剪贴板可能整体不可用
**症状**：页面 `writeText` 显示成功但 `readText` 返回空；PowerShell `Get-Clipboard` 报 "Requested Clipboard operation did not succeed"；MCP read_clipboard 报 native clipboard unavailable。疑似 360 安全卫士剪贴板保护或会话锁定所致。
**对策**：**永远不依赖读系统剪贴板**。先装拦截器（hook `navigator.clipboard.writeText` 存进 `window.__capA` + copy 事件兜底 `__capB`），点复制按钮后直接从 JS 变量取。已封装（`wb.install_interceptor` + `wb.read_captured`）。

### G5. 页面里有两种 Copy 按钮
**症状**：点到了"复制"但截获到的是用户的提问文本甚至空串。
**原因**：x≈819（右侧）是用户提问消息的复制按钮；x≈171（左侧）是 AI 回复的复制按钮。位置随滚动变化，不能按坐标猜。
**对策**：永远取 `querySelectorAll(copy_css)` 的**文档序最后一个**（即最新一条回复），再按可见性决定是否滚动。已封装。

### G6. scrollIntoView 后坐标是"滚动动画进行中"的瞬时值
**症状**：滚动→量坐标→点击→落空（页面用平滑滚动，~500ms 动画）。
**对策**：scrollIntoView 后 **sleep 2.5s** 再重新量坐标，再点击。已封装。

### G7. 长回复的复制按钮在视口外上万像素
**症状**：快照里有 Copy 按钮，但 rect y=-20000 或 y=20000。
**对策**：先判可见性（`bottom>0 && top<innerHeight`），不可见就滚动到它。已封装。

### G8. 生成中的判断：Stop 按钮是唯一可靠信号
**症状**：模型思考期（Qwen3.8-Max 每章 3~10 分钟）页面文字**完全不增长**，看着像卡死；正文流式输出中途也可能长时间停顿（第二段思考）。
**对策**：有 Stop/停止 按钮 = 活着，继续等；完成 = Stop 消失 + 复制按钮数比发送时 +1 + 确认两次（间隔一个轮询周期）。不要用"文字长度稳定"单独判断，思考期会误判。toast 文案（如"Copying to clipboard was successful!"）会混进快照文本，对长度判断有小干扰，无害。

### G8b. 新会话没有"当前标签页"，单标签工具返回 HTTP 502
**症状**：新 session 名下直接调 snapshot/click/fill 报 502 Bad Gateway。
**原因**：WebBridge 的单标签工具只作用于本会话最近 navigate/find_tab 过的标签页。
**对策**：任何会话先 `find_tab {url, active:true}`（借用用户正看的标签页）或 `navigate {newTab:true}`，再进行其他操作。generate.py 已内置；CLI 报 502 时按提示先 `python wb.py open <url>`。

### G9. 发送验证：标记回显 + 输入框清空
**对策**：发送后确认（a）提示词的 distinctive 子串出现在页面文本（用户消息回显），（b）输入框 value 为空。两者同时成立才算发出。标记取提示词最长行的前 12 个非符号字符（`wb.pick_marker`）。空编辑器点 Send 无副作用（千问忽略），安全。

## 思源侧

### G10. 端口每次启动都漂移
**症状**：写死 6806 时 `code:0` 但写入静默丢失（连到了旧内核实例）。
**对策**：永远从 conf.json 顶层 `serverAddrs` 现读（实测本机漂到过 52186）。`siyuan.load_connection()` 已封装。

### G11. 写入校验用 getChildBlocks（活数据），不用 exportMdContent/getBlockKramdown（有缓存）
**对策**：`save_chapter` 写入后 `getChildBlocks` 数块数 <5 判失败。

### G12. 思源 KaTeX 兼容清洗（不清洗则公式整块渲染空白）
- `\qquad`/`\quad` 挤双公式的 `$$` 块 → 拆成独立块；
- `\;` `\,` `\!` → 空格/删除；
- ASCII `~` 是思源下标语法 → 正文里换成全角 `～`，公式内换空格；代码块不动。
- 零宽字符（Qwen 复制内容常带）全部剥除。已封装在 `siyuan.clean_markdown`。

### G13. 章节标题取正文第一个 `## `
文档标题（`createDocWithMd` 的 path 最后一段）不能含 ASCII `/`（会变嵌套空文档）→ 换全角 `／`。正文开头的 `# 大教程名` 一行剥掉（父文档已承载）。同名文档已存在则跳过（幂等，也是断点续传的依据）。

### G14. 内核写入不会自动刷新桌面 UI
**对策**：每次入库成功后调 `/api/ui/reloadUI`，否则用户在思源里"看不到"。

## 流程结构

### G15. 章节重叠是省时的关键
顺序：截获第 N 章内容 → **立刻发第 N+1 章提示词** → 存第 N 章进思源。存思源只要几秒，让 AI 的思考时间与本地工作完全重叠。

### G16. 中途接管用户已开的对话
用户可能已经手动发过第一章（"打个样"）。用 `find_tab {url, active:true}` 借用用户当前标签页（`borrowed:true`），不要开新标签页。自己开的标签页可能被用户关掉，报 `tab was closed` 时重新 find_tab 即可。

### G17. Qwen 复制输出的表格行间夹空行 → 全部表格失效
**症状**：思源里文档"表格块=0"，每一行表格变成独立段落块（伪表格），用户看到的是一堆竖线文本。实测同一教程 6 章里 3 章如此、3 章正常（模型输出不稳定）。
**原因**：Qwen 的复制内容有时是 `| 行1 |\n\n|---|---|\n\n| 行2 |`——GFM 要求表格行连续，夹了空行就不再是表格。
**对策**：入库前 `join_table_rows()` 把夹在表格行之间的空行删掉（跳过代码围栏）；入库后 `audit_doc()` 校验表格块数=源表格数、无伪表格段落。已内置在 `siyuan.save_chapter`，校验失败自动删除坏文档并报错。

### G18. 入库前后格式校验清单（每章必做）
- **入库前**（源 Markdown）：代码围栏成对（奇数个 ``` = 内容截断，拒收）；表格分隔行存在且各行列数=表头；`$$` 配对。
- **入库后**（getChildBlocks 活数据）：表格块数=源表格数；无"以 | 开头的段落块"（伪表格）；公式块无 `\;` `\,` `\quad` `\qquad` `\(\)` `\[\]` `<sup>` 禁词。
- 失败处置：删除刚建的文档并报错，绝不留坏文档（否则断点续传会把它当"已完成"跳过）。

### G19. 代码围栏里的 `##` 不能当标题
章节标题取"第一个 `## ` 行"，必须逐行扫描并跳过代码围栏——Python 注释 `## 说明` 在围栏里会被 re.M 误当标题。同理 `re.match` 锚定全文开头，若正文以 `# 教程名` 开头则永远匹配不到 `## `（标题会静默退化成兜底名）。`title_from_md` 已按围栏感知实现，且必须传"剥掉 H1 之后的正文"。
