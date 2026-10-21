---
name: paper-figures
description: "学术论文图表、视觉摘要与学术海报全流程生产中枢。内置顶刊版面预设（Nature/Science/Cell/IEEE/Elsevier）、色盲无障碍（CVD）与灰度仿真质检、多子图马赛克拼版（subplot_mosaic）、Graphical Abstract 双轨生成（1:1方版/2.5:1横版）、0度水平文字铁律、OpenXML DrawingML 原生矢量控制、中文标点避头尾禁则与数据诚信契约。支持五大管线路由：投稿级矢量数据图与3D爆炸图、PPT示意图转矢量、Origin直通可编辑OPJU、Graphical Abstract视觉摘要双轨、学术海报易拉宝双轨。Triggers: 画论文图, 画个图, 绘制图表, 论文插图, 科研画图, 数据画图, figure for paper, IEEE figure, plot paper figure, Origin 画图, OriginPro 可编辑图, OPJU, 导师要 Origin 格式, 图命名, 图放哪, 转成矢量图, ppt转pdf, 坐标画布, 元素移动, 标签位置, 图上定位, 爆炸图, 层级图, 3D 结构图, exploded view, 子图题注, subcaption, 学术海报, 海报设计, 易拉宝, 会议海报, 论文海报, academic poster, poster pptx, 导出pptx, 可编辑海报, 易拉宝排版, 海报绘图, poster design, rollup banner, 展板设计, 学术展板, 海报转pptx, 海报导出可编辑, matplotlib转pptx, 双轨一致性, Nature绘图, Science绘图, 顶刊插图, 视觉摘要, graphical abstract, 色盲检测, 色盲友好, check colorblind, 多子图拼版, multipanel, 子图拼图, 柱状图散点, 统计图绘图."
metadata:
  version: "1.6.0"
  last_updated: "2026-10-18"
  status: active
  data_access_level: raw
  task_type: open-ended
  related_skills:
    - academic-paper
    - ieee-engineering-paper-writer
---

# paper-figures — 学术论文图表与海报生产（统一入口）

本技能提炼自 Nature/Science/Cell 顶刊标准、IEEE 旗舰期刊实战、Origin 直通管线，以及会议易拉宝（60cm × 160cm）双轨高保真排版全流程经验。
**第 0 步永远是路由**；本技能下沉了全流程共享的底层标准（0 度水平文字、PPTX 原生矢量引擎、色盲安全质检、标点避头尾禁则、数据诚信契约），向上赋能五大专业业务管线。

---

## 零、管线选择（第 0 步）

| 需求场景 | 走哪条管线 | 核心交付物 |
|---|---|---|
| **投稿级矢量数据图 / 3D 爆炸图** | §二·1 matplotlib 顶刊管线 | `fig<N>_<slug>.pdf` + `.png` + `_notes.txt` |
| **论文示意图（架构/装置/流程），要在 PPT 里手调** | §二·2 PPT 原生图 + 转矢量 | 原生可编辑 `.pptx` + 实测包围盒裁剪矢量 PDF |
| **导师/合作者要 Origin 风格、可编辑 OPJU** | §二·3 Origin 直通管线 | `result.opju` + `pdf/png/tif` + 审计报告 |
| **Graphical Abstract（视觉摘要）投稿** | **§二·4 视觉摘要双轨管线** | 1:1 或 2.5:1 矢量 PDF + 对应可编辑 `.pptx` |
| **学术海报 / 易拉宝 / 会议展板** | **§二·5 海报双轨交付管线** | 300 DPI CMYK `poster.pdf` + 1:2 可编辑 `poster.pptx` |

- **拿不准时不要反问**：
  - 给了数据文件、没说用途 → 默认按投稿向 matplotlib 做，交付时提一句“要给导师改，可再出 Origin 版”；
  - 明确提到视觉摘要 / Graphical Abstract → 走 §二·4；
  - 明确提到海报/易拉宝/展板/Poster → 走 §二·5 双轨交付（严禁仅给单向位图）。

---

## 〇·五、本机固定运行环境

本文件里所有 `python` / `python3` **一律指下列绝对路径**。WorkBuddy 托管运行时（`~/.workbuddy/binaries/python/versions/*/`）是隔离环境、**零第三方包，不要用**。

| 管线 | 解释器绝对路径 | 包含包 |
|---|---|---|
| matplotlib / PPT 原生图 / 海报双轨 / 视觉摘要 / 质检比对 / 色盲检测 | `C:/Users/qilin/miniconda3/python.exe` | matplotlib, numpy, python-pptx, pywin32, reportlab, PyMuPDF (fitz), Pillow, SciPy, PyYAML |
| Origin 直通 | `C:/Users/qilin/miniconda3/envs/editaplot/python.exe` | CPython 3.12 + `origin/engine/requirements-runtime.lock` |

---

## 一、全管线共用底层铁律与公共中枢（Shared Core）

无论是论文单双栏插图、Graphical Abstract 还是 160cm 易拉宝，以下六大底层标准由全管线**强制共享**：

### 1.1 【0 度水平文字与无遮挡遮罩铁律】
- **严禁文字倾斜**：无论流程箭头、数据连接线是 $30^\circ$ 还是 $45^\circ$，上面的标注文字**必须 100% 保持 0 度水平**，严禁使用 `rotation=angle` 让文字倒挂或斜躺！
- **纯白防穿帮遮罩**：当连线穿过文字区域时，文字必须配置纯白/背景色遮罩（带 padding），避免线条横穿字迹（matplotlib 使用 `bbox=dict(facecolor='white', pad=2.0)`，PPTX 使用 `pptx_core.create_horizontal_callout`）。
- **垂直容器自然竖排**：纵向长矩形容器内部汉字采用单字换行流自然堆叠（`内\n容\n联\n动`），绝不旋转文本框 90 度。

### 1.2 【色盲友好 (CVD) 与灰度打印安全质检】
- **痛点**：红绿色盲占男性约 8%，传统红绿对比图会被 Nature/Science/IEEE 严厉挑刺；黑白灰度打印下曲线易粘连。
- **工具调用**：运行 `python scripts/check_colorblind_safety.py <fig.pdf|png>` 自动生成 4 联质检图（原始图、绿色盲仿真、红色盲仿真、纯黑白灰度打印仿真）。
- **安全色板**：优先选用 `scripts/color_palettes.py` 中的 **Okabe-Ito 配色**（8 色全无障碍）或 **Paul Tol 配色族**。
- **冗余编码**：绝不仅依赖颜色区分数据，必须叠加点型（圆/方/三角）或线型（实线/虚线）。

### 1.3 【中文排版与标点避头尾禁则（CJK Kinnsoku Shori）】
- **痛点**：全角逗号 `，`、句号 `。`、分号 `；` 掉落至下一行行首，破坏学术庄严度。
- **三大对策**：
  1. 文本框按字号预留 2–3mm 标点避让缓冲区；
  2. 语法意群主动断行法：复杂长难句在多分句逗号处主动显式断行（`，\n`），锁定逗号在句尾；
  3. 标签悬挂对齐：使用加粗标签 `【标签】` 与正文在同一段落流式排布。

### 1.4 【python-pptx 原生矢量引擎（pptx_core.py）】
所有可编辑 PPTX 生成必须基于公共库 `scripts/pptx_core.py`：
1. **`<a:ea>` 东亚字体声明**：注入 XML，确保思源宋体/黑体在 Windows Office 中生效不回退；
2. **`adj=3000` 微圆角控制**：消除默认 `adj=16667` 过圆的移动端廉价感，获得端庄卡片；
3. **彻底清除 `<a:effectLst>` 阴影**：维持现代扁平矢量风格；
4. **文本框四向边距清零 (`margin=0`)**：保证排版净宽完全符合设计计算。

### 1.5 【双轨视觉一致性（Visual Parity）质检闭环】
运行 `python scripts/verify_visual_parity.py <fig.pdf> <fig.pptx>`：
PyMuPDF 渲染 PDF 为 300 DPI 基准图 $\to$ PowerPoint COM 无头静默导出 PPTX 为同等 PNG $\to$ 单图拼接或长图 4 视区切片比对 $\to$ 自动化检测标点孤悬、0 度文字与文字截断。

### 1.6 【数据诚信与统计契约（Statistical Integrity）】
- **柱状图零基准硬铁律**：表达数值量级或比例的柱状图，**Y 轴绝对必须从 0 开始**，严禁截断起始坐标夸大差异！若展示微小波动应改用折线图并带 `//` 断轴标志。
- **原始散点叠加**：样本量 $n \le 50$ 的柱状图/箱线图，上方必须叠加半透明抖动真实散点（Jittered Stripplot），展示分布真实性。
- **误差线与星号**：必须在同名 `_notes.txt` 中严格声明误差线定义（SD vs SEM vs 95% CI）与单调显著性口径（$*p<0.05, **p<0.01, ***p<0.001$, ns）。

---

## 二、专门业务管线实现指南

### 2.1 管线 A：投稿级 matplotlib 数据图与顶刊预设
- **期刊尺寸预设**：直接调用 `scripts/journal_profiles.py`：
  ```python
  from journal_profiles import apply_journal_style, get_journal_figsize, add_panel_label
  apply_journal_style("nature")  # 或 science, cell, ieee, elsevier
  figsize = get_journal_figsize("nature", columns="double")  # 自动换算 mm 为 inch
  ```
- **多子图统一拼版**：直接调用 `scripts/multipanel_mosaic.py`，使用 ASCII 字符布局与自动标号：
  ```python
  from multipanel_mosaic import create_multipanel_figure
  fig, axd = create_multipanel_figure("""
      AAB
      AAC
      DDD
  """, journal="nature", columns="double")
  ```
- **3D 爆炸图 (mplot3d)**：层序表先行，侧视视角 (elev 14–22°)，单个 Poly3DCollection 组装，严禁 `computed_zorder=False`。

### 2.2 管线 B：论文示意图 PPT 构建与 PPT $\to$ 矢量转换
用途：用户/导师要在 PPT 里调版式的装置图、拓扑图、架构图。
1. **2× 尺寸建页**：图宽 3.5 in $\to$ 幻灯片宽 7.0 in，字号线宽同步翻倍；
2. **构建原则**：引入 `pptx_core`，卡片用 `create_card`，胶囊用 `create_pill_badge`，连线文字用 `create_horizontal_callout`；
3. **转矢量出图**：运行 `python scripts/pptx_to_vector.py <file.pptx> --name figN_slug`：
   PowerPoint COM 导出整副 PDF $\to$ PyMuPDF 逐 shape 实测内容包围盒裁剪（0.05 in 细边）$\to$ 同步产出 600 dpi PNG。

### 2.3 管线 C：Origin 直通可编辑图表（OPJU）
用途：导师/合作者要求 Origin 格式工程图。
- 解释器：`C:/Users/qilin/miniconda3/envs/editaplot/python.exe`
- 一条命令直通：
  ```bash
  C:/Users/qilin/miniconda3/envs/editaplot/python.exe \
    C:/Users/qilin/.zcode/skills/paper-figures/origin/scripts/origin_fig.py direct <data.csv> \
    --template trend --claim "科学论断" --x-title "Time (s)" --y-title "Power (W)" \
    --x t_s --y "power_W" --auto --name fig3a --output-dir <out>
  ```
- 数据守卫全自动生效，产出 `result.opju` + `pdf/png/tif` + 冻结计划与校验报告。

### 2.4 管线 D：Graphical Abstract（视觉摘要）双轨生成管线
为 Elsevier、Cell Press 等期刊提供投稿用视觉摘要，**双轨交付**（印刷级 PDF + 原生可编辑 PPTX）：
- **Square 模式 (1:1 比例)**：$1200 \times 1200\text{ px}$ (Cell Press / ACS / RSC 标准)，模板 `template_graphical_abstract.py` 中的 `draw_graphical_abstract_square`；
- **Banner 模式 (2.5:1 比例)**：$1328 \times 531\text{ px}$ (Elsevier / Springer 标准)，模板 `draw_graphical_abstract_banner` 与 `template_graphical_abstract_pptx.py`；
- **视觉逻辑**：三段式流向【输入/挑战】 $\to$ 【核心机制/技术干预】 $\to$ 【性能/成果】。

### 2.5 管线 E：学术海报与易拉宝双轨交付管线（Poster & Roll-Up Banner）
当需求为学术展板、会议易拉宝时触发：
- **物理印刷规范**：成品 60cm × 160cm（含 3mm 出血为 60.6cm × 160.6cm），安全边距 2.0cm，**底部必须留白 5.5–6.2 cm** 防止转轴吞字；
- **PowerPoint 1:2 缩放铁律**：破除 Office 56 英寸限制，PPTX 严格设为 $30.0\text{ cm} \times 80.0\text{ cm}$，字号严格折半（**正文 $\ge 15.0\text{pt}$ 硬底线**）；
- **黄金四段式版面**：Header 24cm $\to$ Sec1 22cm $\to$ Sec2 24cm $\to$ Sec3 56cm $\to$ Footer 24cm；
- **模板与质检**：`template_poster_pdf.py` + `template_poster_pptx.py`，最后调用 `verify_visual_parity.py` 闭环。

---

## 三、工具库速查表（`scripts/`）

| 脚本文件 | 核心职责 | 关键方法 / 适用场景 |
|---|---|---|
| **`journal_profiles.py`** | 顶刊排版尺寸与预设 | `apply_journal_style("nature")`, `get_journal_figsize`, `add_panel_label` |
| **`color_palettes.py`** | 学术色盲安全调色板 | `set_academic_palette("okabe_ito")`, `OKABE_ITO`, `PAUL_TOL_VIBRANT` |
| **`check_colorblind_safety.py`** | 色盲 (CVD) 与灰度打印质检 | 一键输出 4 联色觉仿真图，排查红绿混淆与黑白对比度 |
| **`multipanel_mosaic.py`** | 多子图 ASCII 马赛克拼版 | `create_multipanel_figure(mosaic, journal="nature")`，自动子图标号防撞 |
| **`pptx_core.py`** | 原生 PPTX 矢量控制底层库 | `<a:ea>` 字体声明、`adj=3000` 微圆角、清除阴影、清零边距 |
| **`verify_visual_parity.py`** | PDF vs PPTX 双轨视觉一致性检验 | PyMuPDF + COM 无头导出 + 单图/长图切片比对 |
| **`template_graphical_abstract.py`** | 视觉摘要矢量 PDF 生成器 | 1:1 方版 (Cell) 与 2.5:1 横版 (Elsevier) 模板 |
| **`template_graphical_abstract_pptx.py`** | 视觉摘要可编辑 PPTX 模板 | 基于 `pptx_core`，原生三段式模块，双击即改 |
| **`template_poster_pdf.py`** | 易拉宝印刷级 PDF 模板 | ReportLab 60.6x160.6cm、CMYK、出血角线、底座留白 |
| **`template_poster_pptx.py`** | 易拉宝 1:2 可编辑 PPTX 模板 | 30x80cm 规格、全原生矢量、正文字号 $\ge 15\text{pt}$ |
| **`canvas.py`** | 坐标画布协议与碰撞检测 | `Canvas(fig)`，输出 `*_grid.png` 与 `*_layout.txt` 坐标清单 |
| **`pptx_to_vector.py`** | PPT 示意图转出版级矢量 PDF | COM 导出整副 PDF + PyMuPDF 实测包围盒裁切 |

---

## 四、与用户的交互红线

- **用户说“改好了让你翻译/导出”之前，绝不碰用户的 PPT/图文件**——不覆盖、不“顺手刷新”、不恢复旧版。
- 转换用 `DispatchEx`（独立进程），用户开着 PowerPoint 时**永不 Quit**、不附加其会话。
- 用户对版式的手工调整优先级高于脚本；以用户文件为准，先问再覆盖。
- 海报与视觉摘要任务**严禁仅交付图片或单向 PDF**，必须主动奉上可自由修改的 PPTX 源码并声明缩放比例。
- **出图后自查四部曲**：① 图内文字是否 0 度水平？② 有无孤悬标点掉落行首？③ 色盲质检是否通过？④ 柱状图 Y 轴是否从 0 起始？
