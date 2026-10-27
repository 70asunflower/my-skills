---
name: svg-diagram-pipeline
description: 在思源笔记文章里插入示意图/原理图的完整工作流——先画 SVG 交互图（会话内预览确认），再无头 Chrome 渲染静态 PNG，上传思源 assets 后插入或替换正文插图并校验；含 MOSFET 等电路原理图的标准符号语法。当用户要求"画示意图/原理图/结构图/配图/电路图"且内容要放进（或可能放进）思源文档时使用；纯会话预览无思源环节时只用前两步。
---

# SVG 示意图 → 思源文档 流水线

把"画图 → 进文档"固化成五步。每一步都有已验证的命令与已踩过的坑，按顺序执行，不要跳过目检。
配套脚本在 `scripts/`（build_mini.py / shoot.bat / upload_swap_asset.py），直接用，勿重写。

## 流水线总览

```text
① 绘制交互图（Write HTML → 会话内 ::visualize 预览，用户确认）
② 渲染静态 PNG（Remotion 无头 Chrome，2x）
③ 上传思源 assets（/api/asset/upload，字段 file[]）
④ 插入或替换正文插图（insertBlock / updateBlock）
⑤ 校验刷新（getChildBlocks 断言 + /api/ui/reloadUI）
```

## 第 1 步｜绘制交互图

- 写入会话可视化目录：`D:\MyData\Zcode\.zcode\v2\visualizations\<会话哈希>\<名称>.html`（纯 HTML 片段，无 doctype/html/head/body）。
- 颜色：**确定要出 PNG 进文档的图，会话版与渲染 mini 版合一**——全部硬编码 hex + 显式白底，只维护一份文件（2026-10-16 定案，免掉双版本同步）。纯会话 UI 类交互（不出 PNG）才用 `var()` 主题变量。
- 回复末尾输出 `::visualize{"path":"<绝对路径>"}` 让用户在会话里预览、提修改意见。
- **布局四条铁律**（都踩过坑）：
  1. 所有元素坐标必须在 viewBox 内——读数框/图例/右侧标签超出 viewBox 会被裁掉（踩过 ×2：输出框被裁、电压图右侧标签被裁）。
  2. 文字与图形、文字与文字留 ≥6px 间距；说明文字加白色衬底矩形再压在线条密集区上（踩过：说明文字与光束线条交叉穿行）。
  3. 长标签先估算像素宽（中文 ≈ 字号 × 字数），确认不与相邻元素重叠再落笔。
  4. 每条文字落笔前，把它的包围盒和图内**所有**线段做一次相交自查——不只查相邻元素（踩过：电流标签正好压在输出竖线和箭头上）。

## 第 1.5 步｜电路原理图专项：MOSFET 符号语法

画晶体管级电路按教科书符号来，否则用户会批"晶体管看着不像"（2026-10-16 整轮返工教训）：

1. **沟道是粗棒**：stroke 11（引线用 4）。细线沟道会和引线融成一根长线，整图读成"电线加两道杠"——这是"不像"的头号根因。
2. **栅极板短且留隙**：长度约沟道 70%（两端各缩 15%），与沟道间距 ≥20。等长栅板读不出"栅极"。
3. **漏极横向引出**：PMOS 漏极从沟道底部竖走 ~20 再横向拐向输出节点，NMOS 从顶部对称处理——这个"肩膀"是器件感的来源。串叠级间（源→下一级漏）可以共线直连，靠粗沟道棒提供器件感。
4. **PMOS 用栅极气泡**区分，NMOS 无泡。气泡/端子圆圈要白底必须写 `style="fill:#ffffff"`——class 里的 `fill:none` 会覆盖 `fill="#ffffff"` 表现属性（踩过：气泡透明，底色从圆圈里渗出来）。
5. **并联对**（如 NAND 下拉管）：共享总线两端必须**超出管位**留头，每个 T 形交点打实心圆点；两条等长笔直总线会把两管围成一个"矩形框"，读成一个怪器件。
6. **同名栅极**（并联管同信号）：一只接真实总线，另一只画短引线+圆点+网络名（A/A、B/B），避免绕线交叉。
7. **状态编码用颜色+文字双通道**：导通管深色、截止管整体灰化+栅线虚线、双管半导通红色标注（"过渡区"）。电流方向用红线+实心三角箭头，标签放空白区。

## 第 2 步｜渲染静态 PNG

- **不要用** playwright（本机未装）、**不要用** visualize skill 的 render.py（bundled hash mismatch 报错）、**不要用** Edge msedge.exe 无头（`Input redirection is not supported` 或 rc=0 无产物，纯浪费时间——2026-10-16 踩过一整轮）。
- **用** Remotion 缓存的无头 Chrome（本机已验证）：

```text
D:\Project\Zcode\college-promo\node_modules\.remotion\chrome-headless-shell\win64\chrome-headless-shell-win64\chrome-headless-shell.exe
```

- 流程（scripts/ 里现成）：

```cmd
python <skill>/scripts/build_mini.py <片段.html> D:/tmp/<名>-mini.html
call <skill>/scripts/shoot.bat file:///D:/tmp/<名>-mini.html D:\...\out.png "2000,1090"
```

- ⚠️ shoot.bat 在 ZCode 的 cmd 包装下可能报 `< was unexpected at this time.`（2026-10-18 实测）——此时改用 subprocess runner 直调 Chrome，参数同 bat：`subprocess.run([CHROME,"--headless","--disable-gpu","--hide-scrollbars","--force-device-scale-factor=2","--default-background-color=FFFFFFFF",f"--window-size={w},{h}",f"--screenshot={out}",url])`。

- `--force-device-scale-factor=2` 出 2x 图（打印清晰）；窗口高度 = 内容高，宁大勿小。
- **渲染后必须 Read PNG 目检**：文字重叠、元素出画布、颜色丢失都只能靠目检发现（踩过 ×4）。整图之外再对重点区域做一次 PIL crop 放大——缩略整图上深色小字形会有摩尔纹假象（圆圈里的 X 看似红叉），crop 后再下结论。
- cmd 坑：没有 heredoc、没有 `tail`；批量修改 SVG 写成 `patch_*.py` 脚本文件执行，别用 `python - <<EOF`。

## 第 3 步｜上传思源 assets

- 内核端口**每次启动漂移**：从 `D:\MyData\Warehouse\siyuan-backup\conf\conf.json` 顶层 `serverAddrs` 现读（勿写死 6806）。
- 接口：`POST /api/asset/upload`，multipart，**字段名必须是 `file[]`（带方括号）**。
- ⚠️ 已踩坑：写字段 `file` 返回 `code:0` + 空 `succMap` 的**静默失败**——磁盘上没有文件，接口却不报错。判定成功只看 `succMap` 非空。
- 解析 `resp["data"]["succMap"]` 取路径——**返回值已含 `assets/` 前缀**，插图模板里不要再拼一层（拼了会写出 `assets/assets/…` 而对不上真实文件，图静默不显示；2026-10-27 踩过：succMap 正常返回、磁盘有文件，唯独 URL 双前缀）。

## 第 4 步｜插图进文档

**替换已有插图**（迭代改图时更常用）：

1. `getChildBlocks(文档ID)` 找到 markdown 含旧 asset 文件名的图片块。
2. `updateBlock` 同一块，data 换成新 `![题注](assets/新文件.png)`——题注 alt 顺手修正（踩过：alt 文字被截断）。
3. 断言：新 asset 恰好 1 处、旧 asset 0 处、总块数不变。多张图逐图断言，最后统一 `reloadUI` 一次。
4. scripts/upload_swap_asset.py 已封装 1–3：改顶部配置区（DOC_ID + JOBS）即可跑。

**全新插图**：

1. 先 `exportMdContent` 或 `getChildBlocks` 通读目标文档，确定插图锚点（图片应紧跟的那块）。
2. `POST /api/block/insertBlock`：`{"dataType":"markdown","data":"![题注](assets/xxx.png)","previousID":"<锚块ID>"}`。
3. ⚠️ **校验时别查错文档**：锚点属于哪篇文档就 `getChildBlocks` 哪篇（踩过：插图插入 A 文档、却对 B 文档做邻接校验，误报"锚点不存在"）。

## 第 5 步｜校验与刷新

- `getChildBlocks(<文档ID>)` 断言：新插图块在位（markdown 含 assets 路径）、旧引用清零、块数符合预期。
- `POST /api/ui/reloadUI` —— 内核写入不会自动刷新思源界面，不刷新用户就是"看不到"（§12.9 类问题）。

## 设计约定（把图画清楚的规则）

- 一张图一个主题；先列元素清单再落笔画。
- 状态/方向用 **颜色 + 形状/文字** 双重编码，不只靠颜色。
- **字体与中文字距防坍塌铁律（2026-10 实测血泪教训）**：
  1. **字号绝对下限**：中文字号**必须 $\ge 11\text{px}$**（严禁 $9.5\text{px} \sim 10\text{px}$）。在 Windows Chromium/DirectWrite 下，小于 11px 的中文汉字字宽会被误计为 0，导致整行汉字向左坍塌、重叠挤成黑块。
  2. **严禁在同一 `<text>` 内混入 Unicode 图标/符号**：严禁在正文汉字前写 `●`、`❌`、`✔`、`★`、`▲` 等特殊符号。这些字符来自 Symbol 回退字体，切回中文字体时会导致光标水平前进量错乱，引发字符重叠。图标一律改用 SVG 纯矢量绘制（如 `<rect>` 药丸徽章 `[阻断]`、`[压缩]`、`<circle>` 状态圆点，或独立定位的单独 `<text>`）。
  3. **字体栈中文优先**：`font-family="'Microsoft YaHei', 'PingFang SC', sans-serif"`。严禁以英文字体（如 Segoe UI）开头，否则符号/括号/标点切换字体会导致后接汉字基线与字距错乱。
  4. **行高呼吸间距**：两行文字 baseline 间距必须 $\ge 20\text{px}\sim 24\text{px}$（字号 12px 时）。严禁 14~16px 的极限间距。
- **消除空洞与紧凑构图法则（Anti-Blankness）**：
  1. 外层容器与 viewBox 高度必须与卡片紧密咬合（例如内部卡片 190px，则容器 210px，外层 viewBox 280~310px 即可）。严禁 viewBox 520px 而内容仅 200px 留出 100px+ 巨大空洞。
  2. 内部卡片纵向空间自然饱满：采用“标题栏 + 载荷展示区 + 系统工程属性区”分层填充，杜绝卡片内部大块空白。
- **连线与跨越安全边距**：
  1. 连线箭头上下标注的长标签（如 `W_embed[id]`），跨度必须大于文字宽度 + 16px 安全边距，否则会被相邻卡片边框遮挡剪裁。
  2. 中文像素宽估算：中文字数 × 字号 + 8px；英文按 6~7px/字符估算。
- 电路/流程类：先定骨架（rail → 器件 → 节点 → 输出），再补标签，最后加图例；晶体管符号照第 1.5 步语法。

## 资产命名与版本

- 上传文件名用 `sym-<图号>-v<K>-<6位随机>.png` 递增版本；succMap 返回的路径才是权威路径。
- 旧版本资产留在 `assets/` 不删（无引用即无害）；文档永远只指向最新版。

## 与设计文档的联动

正式项目（如《100G 自由空间激光通信点对点链路设计方案》）改了选型/参数后，**全文审查一遍示意图引用是否过期**（幽灵引用：已删器件、旧口径数字、旧型号 SKU），同步改图并重截。
