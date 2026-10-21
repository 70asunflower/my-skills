---
name: paper-figures
description: "学术论文/科研图表生产统一入口，三条管线按用途路由后执行：投稿级矢量 PDF→matplotlib 数据图；导师/合作者要 Origin 风格可编辑图→Origin 直通（OPJU+PDF/PNG/TIF，数据守卫）；示意图（架构/装置/故障树/拓扑）或要 PowerPoint 手调→python-pptx 原生形状+COM 转矢量。含 fig<N>_<slug> 命名与 pdf+png+notes 三件套、坐标画布迭代约定（*_grid.png 网格 + *_layout.txt 坐标表，用户报坐标即改，定位不走截图）；数据完整性硬规则：不插值、不平滑、不造数、标注逐点核对。Use whenever 用户要画论文图、科研数据图、把数据绘成出版级图、提 OPJU/Origin 格式、报告图件问题（文字重叠/图太乱/图太大/出界）或要把 PPT 图转矢量——即使没明说'论文'二字。Triggers: 画论文图, 画个图, 绘制图表, 论文插图, 科研画图, 数据画图, figure for paper, IEEE figure, plot paper figure, Origin 画图, OriginPro 可编辑图, OPJU, 导师要 Origin 格式, 图命名, 图放哪, 转成矢量图, ppt转pdf, 坐标画布, 元素移动, 标签位置, 图上定位, 爆炸图, 层级图, 3D 结构图, exploded view, 子图题注, 多面板题注, subcaption, subfig, subfloat, 面板拆分, 面板导出."
metadata:
  version: "1.4.0"
  last_updated: "2026-10-10"
  status: active
  data_access_level: raw
  task_type: open-ended
  related_skills:
    - academic-paper
---

# paper-figures — 学术论文图表生产（统一入口）

从 IEEE Satellite 2026 论文（Jetson Thor 辐照实验）图 1–5 全流程实战沉淀的约定与工具，后并入 Origin 直通管线。**第 0 步永远是路由**；命名存储约定对三条管线通用。

## 零、管线选择

| 需求 | 走哪条 |
|---|---|
| 导师/合作者要 **Origin 风格、可编辑 OPJU** | §五 Origin 直通 |
| 投稿级矢量 PDF（IEEE 双栏、注释体系、断轴） | §二 matplotlib |
| **堆叠结构 3D 爆炸图 / 层级关系图** | §二 matplotlib + §二·五 专项 |
| 纯示意图（装置图/架构图/故障树/拓扑），或要在 PPT 里手调版式 | §三 PPT 构建 + §四 转矢量 |

- **拿不准时不要反问**：给了数据文件、没说用途 → 默认按投稿向 matplotlib 做，交付时提一句"要给导师改，可再出 Origin 版"；只有明确提导师/Origin/OPJU 才走 §五，明确是示意图/结构关系才走 PPT。
- 同一份数据两条路不冲突：Origin 版给导师改，matplotlib 版进稿。

## 〇·五、运行环境（本机固定，先读这段）

本文件里所有 `python` / `python3` **一律指下列绝对路径**。WorkBuddy 托管运行时（`~/.workbuddy/binaries/python/versions/*/`）是隔离环境、**零第三方包，不要用**。

| 管线 | 解释器 |
|---|---|
| §二 matplotlib / §三 python-pptx / §四 PPT→矢量 | `C:/Users/qilin/miniconda3/python.exe`（matplotlib、numpy、python-pptx、pywin32、PyMuPDF、Pillow、PyYAML、SciPy 齐备） |
| §五 Origin 直通 | `C:/Users/qilin/miniconda3/envs/editaplot/python.exe`（CPython 3.12 + `engine/requirements-runtime.lock`） |

`origin/scripts/origin_fig.py` 的引擎根按**脚本自身位置**解析，所以本技能被联接/复制到别处仍可用；只有 §五 示例命令里写死的 `C:/Users/qilin/.zcode/...` 需换成实际技能目录下的同路径。

## 一、命名与存储（硬约定，三管线通用）

- **定稿目录**：论文仓库中 LaTeX **实际引用**的 figures 目录（当前 Satellite 仓库 = `paper_satellite2026/figures/`，以 main.tex 的 `\includegraphics` 路径为准；根目录 `figure\` 是旧图集）。**草稿绝不进 figures 目录**（草稿预览放 image-cache 或项目工作区 tmp/），定稿才写入；入库遵循该仓库 AGENTS.md（git 提交 + 同名 .log.md，中文路径禁作 git argv）。
- **命名**：`fig<N>_<slug>`，N = 论文图号（占位符 `[图 x: 备注]` 定的号）。备选/rebuttal 素材用 `fig_backup_<slug>`，与正文五图区分。改版覆盖同名文件，不留 `*_v2` 垃圾。
- **三件套**：`fig<N>_<slug>.pdf`（矢量，LaTeX 用）+ `.png`（600 dpi）+ `fig<N>_<slug>_notes.txt`（事件时刻表、各标注的数据依据、被图形省略的细节、诚实边界——图注与正文的素材库）。
- **脚本**：放项目工作区（如 `桌面cache\雷神上天\时间线重建\`），可重跑、输出直写 figure 目录。脚本 = 图的唯一真相源，改图改脚本重跑，不手改 PDF。Origin 直通用 `--name fig<N>_<slug>` + `--output-dir` 遵守同一约定。
- **LaTeX 引用**：`\includegraphics[width=\columnwidth]{fig<N>_<slug>}` **不写扩展名**（pdfLaTeX 按 pdf→png→jpg 优先级自动选）。单栏图 `\columnwidth`，跨双栏大图 `\textwidth`。**SVG 不要用**（pdfLaTeX 不直接支持）。

## 一·五、坐标画布协议（人机定位语言，matplotlib 与 PPT 管线通用）

痛点：AI 盲画、用户看图只能说"往左一点/太低了"，AI 再截图猜像素，一轮反馈烧好几个来回。协议：**先建带坐标的画布，一切定位反馈走坐标或元素名，不走截图**。

- **坐标语言**：`fig` = 画布分数坐标 (0–1，原点左下) —— 主语言；`mm` = 距左下角物理毫米 —— 换算辅助；`data` = 数据坐标 —— 只用于需要随轴联动的元素。PPT 管线用 cm（原点左上，y 向下，PPT 惯例）。
- **工具 `scripts/canvas.py`**，matplotlib 脚本里 `Canvas(fig)` 包一手：
  - 文本/箭头/图元一律 `c.text(name, x, y, s, coord="fig")` / `c.arrow(name, xy, xytext, ...)` / `c.register(...)` 注册并放置，**禁止裸 `ax.text` 写完就丢**（经 Canvas 的元素不要再传 transform/xycoords）；
  - `c.save(base)` 在定稿格式之外多出两个**迭代工件**：`*_grid.png`（叠加 0.1 分数网格+边缘刻度+换算条，**无 tight 裁边，像素↔坐标 1:1**）与 `*_layout.txt`（全部元素坐标表 + 程序化碰撞报告）；
  - 复杂版式先 `python canvas.py preview 画布.png --width-in 3.4 --height-in 3.2` 出空白网格画布跟用户对分区，再落元素。
- **反馈循环**（用户不再需要截图定位）：
  - 用户看 `*_grid.png` 直接报坐标或点名："把 `t_tim` 移到 (0.42, 0.35)"、"在 (0.15, 0.82) 加箭头指向连接器"；
  - AI 改脚本里该元素坐标重跑；**先读 `_layout.txt` 碰撞区自修文字重叠，再交用户或 visual-judge**；
  - 截图/放大自查只用于美学判断（配色、线型、观感），**定位一律走坐标**。
- **任意图片取坐标**：`python canvas.py grid 参考.png 参考_grid.png --width-in 3.4 --height-in 3.2` 把网格烧到同事的参考图/用户截图上，用户照着报坐标即可复刻版式。
- **定稿边界**：`*_grid.png` / `*_layout.txt` 是迭代工件，不进 figure 目录、不进 LaTeX；定稿三件套（§一）不变。

## 二、matplotlib 数据图纪律

- **硬约束**：只画真实数据，禁止插值/平滑/重采样瞬态；图上标注的每个数值先回查原始数据逐点核对。
- 时间戳带 +08:00 → `.replace(tzinfo=None)`；相对时间轴用"当日秒数"，别用 naive datetime 的 `.timestamp()`（Windows 按本地时区解释，整体错位）。t=0 定标后要与多源证据校验重合（如遥测硬停恰落在级联时刻）。
- 样式：跨双栏 7.16 in / 单栏 3.5 in；`pdf.fonttype=42`（TrueType 轮廓，期刊拒 Type 3 位图字体）；刻度朝内四边框；≥6 pt 印刷红线；色盲+灰度安全，语义色（正常深蓝、异常深红 #C1272D 系）；线宽：数据 ≥1.0、轴 0.6。
- **空窗压缩**：无数据区间用断轴（分段映射 X(t) + `//` 断点符号 + 浅灰窄条），两侧共用比例尺。
- **白边最小化**（用户硬偏好）：交付图四周留白尽可能少。matplotlib 一律 `savefig(..., bbox_inches="tight", pad_inches=0.02)`（模板与 Canvas.save 默认已带）；PPT 管线走 §四 实测包围盒裁剪（0.05 in 细边）。出图后目检四边，发现大衬边先查 tight 是否生效。
- 🔴 **按"最终印出宽度"建页**（本轮最大的一个根因，出图前必须定）
  - 关系式：**印出字号 = 面板内的设计字号 × (放置宽度 ÷ 面板自然宽度)**。字号随缩放**同步缩**。
  - 反例（本轮实测）：绘图脚本按 `figsize=(3.5, 2.75)`（满栏宽）建页、字号也按那个尺寸定，但排版时面板被放到半栏宽 → 缩放系数只剩 0.42–0.49，**字号同步砍半**（设计 8 pt 印出 3.7 pt，最差 2.4 pt）。
  - 正确做法：出图前先定**这块面板最终印多宽**——单栏满宽 3.5 in、半栏并排约 1.7 in、通栏 7.16 in——**就按那个英寸数建页**，字号直接设 6–8 pt；排版时 100% 放置、不做缩放。这样印出字号可控且各面板一致。
  - **缩小只会更糟**：缩图省的是版面，赔的是可读性。真要救小字，只能重导面板，不是继续缩。
  - 交付时在 `notes.txt` 写明每块面板的**自然尺寸与宽高比**：论文侧要用它算放置高度，以及在并排两块宽高比不同时反解"等高"所需宽度。
  - 并排两块宽高比不同 ⇒ **等宽必然不等高**（用户会说"一大一小"）。反解式 `w_a·ar_a = w_b·ar_b`、`w_a + w_b = 可用总宽 × 0.97`；图件侧的配合是**尽量让并排两块的自然宽高比接近**，或明确报出两者 AR 供论文侧计算。
- **多面板图的子图题注：两条路线，先选路线再出图**（2026-10-10 实战修正；原「一律烙进 PDF、需要换行才改 LaTeX」的写法作废）
  - **路线 A：题注烙进 PDF**（合成图）。Canvas 注册 `c.text("cap_a", 面板中心 x, 底部 y, ha="center")`，主 caption 在 LaTeX 里逐条 `(a) …; (b) …`。适用：单一合成图、各面板**同版式**。
  - 🔴 **路线 A 的硬伤**：烙进去的字随**该面板的放置缩放**一起缩。一张图里各面板按不同系数放到版面上时，同样设计 8 pt 的题注印出来会不一样大——实测三块面板的角标印成 **3.9 / 4.4 / 5.9 pt，差 1.54 倍**，观感就是"有些图缩小了、文字大小就不一样"。**只要各面板的放置缩放系数不相等，就该走路线 B。**
  - **路线 B：题注交给 LaTeX 生成（每面板一个 PDF）**
    - 导出侧：**一个面板一个 PDF，图内不烙 `(a)(b)`**；面板描述交给论文侧。命名 `fig<N><panel>_<slug>.pdf`（如 `fig1a_exploded_view.pdf`），并在 `notes.txt` 里列清面板清单与顺序（论文侧要照抄）。
    - 论文侧写法（IEEEtran，依据官方 `IEEEtran_HOWTO.pdf` 第 10 页）：**必须 `\usepackage[caption=false]{subfig}`**。`caption=false` 不可省，否则 `caption.sty` 会接管主图注格式、把全篇图注改成非 IEEE 样式。
    - 🔴 **不要用 `subcaption` / `subfigure`**：官方 HOWTO 明写 `subcaption` 与 IEEEtran 不兼容（它没有阻止 `caption.sty` 接管的选项）；`subfigure` 已停止维护、且与 `fixltx2e` 等冲突。用户口中的"用 subcaption"指的是**要 LaTeX 生成子图题注这件事**，实现用 `subfig`。
    - `\subfloat` 的**可选参数必须写**，哪怕留空 `\subfloat[]{...}`：完全不写**不生成 `(a)` 标号**；留空则只印 `(a)`、描述放主图注（多数 IEEE 论文的做法）。可选参数里**不含 `(a)` 前缀**——`(a)` 是 `subfig` 生成的，改文字时别把屏幕上看到的前缀写进源码。
    - 版面代价：子图注占版面（每行约 9.6 pt）。**并排两块合计别超 0.97 栏宽**，否则折到下一行或被迫改通栏；通栏浮动体按两栏计费且只能落页顶，代价见对面 `paper-review` 技能 §9。
- **放大图（inset detail）**：inset 背景**半透明**，不整块遮死母图曲线（`ins = ax.inset_axes(...)` 后 `ins.patch.set_alpha(0.85)` 左右，白底带 alpha）；inset 内部的数据与文字保持不透明保证可读；zorder 置顶；母图上画放大区域框并引出线连到 inset（如 fig3 的 Collapse detail）。双 Y 轴 twinx 会反过来盖住 inset，见下条 zorder 处理。
- **图内悬浮文字块加白底**：叠加在图形上的文字块（图例面板、层级列表、区域标注，如爆炸图的 Assembly Hierarchy 面板）必须加白色底框，否则与底层图形互相干扰不可读：`t.set_bbox(dict(facecolor="white", edgecolor="0.6", boxstyle="round,pad=0.3", alpha=0.9))`；底框半透明、文字不透明；此类面板的位置经 Canvas 注册，迭代时在 grid.png 上报坐标微调。
- **防碰撞纪律**（用户最敏感点）：三道工序——① 程序化检查：`_layout.txt` 碰撞区（Canvas 自动报告文字包围盒重叠）；② 标签逐文字放大自查或交 visual-judge agent 验收；③ 双 Y 轴 twinx 会盖住 inset → `ax.set_zorder(axV.get_zorder()+1); ax.patch.set_visible(False)`；竖直参考线附近的文字块要起始于线右侧。
- 实战坑：① 量纲（轨电流 mA 画在 A 轴忘 /1000 → 曲线整条"消失"，出界先查单位换算）；② 时区（naive `.timestamp()` 整体错位，见上）；③ 行内粗体+正文间距用 mathtext `$\mathbf{...}$`（`mathtext.fontset="dejavusans"`）单对象渲染，别用测宽摆两个文本对象（必粘连）。
- **验收循环**：生成 → 自查 → `documents:visual-judge` agent 按验收标准逐项判（传文件路径+要求）→ 修 → 复检。agent 限额不可用时自行放大截查并声明。

模板：`scripts/ieee_matplotlib_template.py`（含全部坑位注释）。实战范例：`C:\Users\qilin\Desktop\cache\雷神上天\时间线重建\plot_fig3_meter_timeline.py`、`plot_fig4_elimination_tree.py`。

## 二·五、3D 爆炸图 / 层级图（mplot3d 专项）

适用：堆叠结构爆炸图、层级关系图。源自 fig1a Thor 模组爆炸图实战（2026-10-09），几何与视觉纪律并重。

- **层序表先行**：动笔前列层序表，每层四要素——层名、尺寸与来源（【官方 STEP 实测】/【官方文档】/【假设】三种标注，假设项必须在 notes 声明）、z-slot、配色。层序按物理叠层从束流入射面到背面列；**出图上下方向由用户表格定**（fig1a：出图倒置，连接器最上、TTP 最下），别按 CAD z 轴默认方向照搬。
- **z-slot 与紧凑感**：层间距紧凑成"一摞"，别散成漂浮板（散=第一版被否的原因）；遮挡启发式 gap > D·tan(elev)（D=板横向尺寸）；需要看穿时上层半透明（alpha 0.4–0.5，如模组 PCB），不用大间隙换可见性。
- **视角=信息，先于坐标检查**：elev 14–22° 接近侧视才有叠层剖面感（太高成俯视平面图，太矮压扁）；azim 与俯视图/数据图同向（fig1a 定稿 elev=20, azim=-75，与 STEP 俯视 QA 图同向）。收到"位置不对"类反馈先分辨**朝向问题**（转 view_init 即可）还是**坐标问题**（回 STEP 全局帧复核）——先出俯视对照图再下结论，不要急着改坐标。
- **遮挡与画法**：全部面进**单个** Poly3DCollection（面内 painter 排序），顶面色 + 侧面 shade(0.88) 出立体感；**禁 computed_zorder=False**（关排序必乱）；埋入层（冷板铜片）画成基板上表面 inlay 贴片，不立独立层；虚线角导引线把炸开的层串回同一立柱（中性蓝 #5B84C4 系，不占语义色）。
- **几何保真**：坐标一律 OCP/STEP 实测（**装配帧 vs 局部帧陷阱**：只有顶层装配迭代给全局坐标，按体积+三维尺寸匹配实体）；**不要把官方偏心布局"居中修正"**（fig1a：SoC/TIM 簇 y 中心 ≈24 vs 模组中心 41.75 是官方事实）；假设尺寸只允许位置假设（die 居中于 TIM 下方）并 notes 声明；交付前跑位置审计脚本出俯视 QA 图留档（verify_fig1a_positions.py 模式：DIM2NAME 匹配 → 坐标表 + 带标注俯视图）。
- **比例与轴**：box_aspect 按 (dx,dy,dz) 真实比例（z 方向可适度夸张但 notes 声明）；mm 轴+刻度。mplot3d 坑位：`axis.line.set_color((0,0,0,0))` 透明化黑轴线、`set_tick_params(length=0, color="none")` 去刻度疙瘩、pane 填充关闭；渲染尺寸=终稿显示宽（3.4in），线≥0.5pt 字≥8pt。第二轮徽章/层名经 Canvas 注册（§一·五），定稿轮次分两步：先纯几何确认，再上标注。
- **实战范例**：论文仓库 `tmp/plot_fig1a_module_exploded_axon.py`（主脚本）+ `tmp/verify_fig1a_positions.py`（位置审计）——tmp 为临时区，引用时确认仍存在。

## 三、PPT 可编辑图（python-pptx）

用途：导师/用户要在 PowerPoint 里手调措辞版式时，把图重建为**原生形状**（绝不贴图）。

- **2× 尺寸建页**：页 = 2×图尺寸（如 3.5→7.0 in），字号线宽同步 ×2——编辑舒适，导出矢量后按目标宽缩回，矢量无损。**之后别改页面尺寸**（它决定裁剪）。
- 元素：圆角卡片 `ROUNDED_RECTANGLE` + `adjustments[0]=radius/min(w,h)`；胶囊徽章 adj=0.5；`shadow.inherit=False` 全部形状；箭头连接线需 XML 加 `a:tailEnd`（见模板 `arrow()`）；下标 `run.font._rPr.set("baseline","-25000")`。
- 文本组织：横幅/卡片标题独立文本框；**列内正文一个文本框、段落=行**（粗体键 run + 数值 run 同段，换行自动流式）——行间距 `line_spacing=1.0`、组间 `space_after`。粗体前缀+正文的词间距由引擎处理，别用测宽摆两个文本对象（必粘连）。
- 断行纪律：断在语义边界（续行以 →/⇒ 开头），不悬挂箭头、不孤词；每条要点尽量单行。
- **坐标画布（§一·五）**：建形状时一律 `shape.name = "t_beam"` 语义名；构建后 `canvas.dump_pptx_layout(prs, "figN_slug_layout.txt")` 出 cm 坐标清单；迭代定位走坐标/点名反馈，不走截图。

模板：`scripts/make_fig_pptx_template.py`。实战范例：`make_fig4_pptx.py`（同目录）。

## 四、PPT → 矢量转换管线

用户改完 PPT 后：`python scripts/pptx_to_vector.py <file.pptx> [--name figN_slug] [--outdir DIR] [--margin 0.05] [--slides 1,2]`

1. PowerPoint COM（pywin32）ReadOnly 打开 → `SaveAs(pdf, 32)` 导出整副矢量 PDF → 逐 shape **实测内容包围盒**（自动适应用户改动）。
2. PyMuPDF `show_pdf_page(clip=bbox+边距)` 裁剪成最终矢量页——内容保持矢量，内嵌照片保持位图。
3. 同步出 600 dpi PNG。命名：单页+`--name` → `figN_slug.pdf/png`；多页 → `<stem>_slide<k>`。
4. 白边默认 0.05 in 细边（用户偏好：小留白，不要大衬边）。**先算包围盒再裁**，别信页面尺寸。

## 五、Origin 直通管线（OPJU 可编辑出版图）

把一份只读数据表变成可审计、可编辑的 Origin 图。引擎 vendored 自 EditaPlot（hang-jin/editaplot，Apache-2.0，LICENSE/NOTICE 在 `origin/` 下），之上新增 direct 模式、数据守卫与本机坑位修复。

- **环境（本机已配好，勿重复操作）**：Windows 实机 + Origin 2025b（COM 注册已验证）。**必须用 conda env `editaplot` 的解释器**（默认 python 3.14 跑不了）：`C:/Users/qilin/miniconda3/envs/editaplot/python.exe`。引擎根 `origin/engine` 由脚本按自身位置自动解析，**勿设 EDITAPLOT_PYTHON**（设了反而让环境探测走错解释器）。
- **一条命令直通**：

```bash
C:/Users/qilin/miniconda3/envs/editaplot/python.exe \
  C:/Users/qilin/.zcode/skills/paper-figures/origin/scripts/origin_fig.py direct <data.csv> \
  --template trend \
  --claim "一句话科学论断（写进图元数据，审计链一环）" \
  --x-title "Time (s)" --y-title "Input power (W)" \
  --x t_s --y "input_power_W,input_voltage_V" \
  --auto --name fig3a --output-dir <out>
```

- `--auto` 开全部数据守卫。产出：`result.opju`（Origin 可编辑）+ `result.pdf/png/tif` + `origin_verify_report.json`（反读校验）+ `render-plan.json`（冻结计划，可复现）。
- **配色**：引擎内置 10 套中文科研配色（8 公开 + 2 受限）。列清单：`C:/Users/qilin/miniconda3/envs/editaplot/python.exe C:/Users/qilin/.zcode/skills/paper-figures/origin/engine/cli/editaplot.py palettes --all --engine-home C:/Users/qilin/.zcode/skills/paper-figures/origin/engine`；`direct` 加 `--palette-id <id>` 把配色合同（HEX、允许模式、分类上限）冻结进 plan。**模式守卫**：数据被判 sequential（如单调梯度）时只接受支持顺序模式的配色，不匹配直接报错拒绝——这是设计不是 bug，换支持该模式的配色或改用默认色。完整规则见 `origin/references/palettes.md`。
- **模板**：常用 `trend`（多系列折线）/`line_error`（误差线）/`scatter`/`heatmap`/`bar`；全量 41 条已验证路线（XPS/XRD/FTIR/NMR/DSC/EIS/ROC/Sankey…）看 `catalog` 子命令。全部子命令只有四个：`direct`（一条命令直通）、`render <plan.json>`（重渲冻结计划）、`merge <a.opju> <b.opju>`（双面板，尽力而为）、`catalog`（列已验证路线）——**没有** `doctor`/`inspect`/`recommend`。
- **数据守卫（--auto 自动，全部源于实战踩坑）**：① 全空行转"只留 X 的部分空行"，防两段数据被假连线；② 宽表多系列网格错开时自动按系列拆图（不插值、不重采样）；③ **永不插值/平滑/补数**是硬红线，引擎与守卫双重拒绝。派生列只放行 identity/scale 白名单，积分等必须上游算好放进 CSV 并在 claim 里声明。
- **已知边界（实测，别再踩）**：
  - trend 单图层一套轴；双 Y 轴、对数轴渲染后在 Origin 里两下点击改（OPJU 全可编辑，别脚本硬做）。
  - LabTalk 带命名参数经 COM 通道**被静默吞掉**（plot 样式、图层矩形、label 定位均实测如此）→ 图面精修去 Origin 界面做，别盲打。
  - merge 子命令尽力而为；双面板可靠做法是图形界面 Graph > Merge Graph Pages（30 秒）。
  - 渲染用独立隔离实例：10–15 s/张正常，30–60 min 无进展先查模态对话框；崩溃残留的 Origin64 进程只清**无窗口**的（有窗口标题可能是用户会话）；连续批量偶发 `origin_instance_start_failed`，direct 已内置清孤儿重试一次。
- **可审计 + 视觉验收**：render-plan 冻结数据 SHA256 + 列角色 + 图元素，verify report 做 Origin 反读核对并断言 `source_data_modified: false`——但这只证数据未被改动，**不保证图面质量**：出图后放大自查 PNG（标签碰撞、量纲、图例）或交 visual-judge，人工检查清单见 `origin/references/verification.md`。
- **细节文档按需读 `origin/references/`**：chart-selection（41 条路线全表与选型）、data-contracts（数据布局识别与修复）、origin-safety（实例生命周期与稳定路线）、verification（校验清单）、palettes（10 套中文科研配色）等。

## 六、文件类型速查

| 场景 | 用什么 |
|---|---|
| LaTeX（pdfLaTeX，IEEE 模板默认） | **PDF 矢量**；`\includegraphics` 不写扩展名 |
| 纯照片单独引用 | PNG/JPG（300–600 dpi） |
| SVG | 不直接进 pdfLaTeX（有矢量 PDF 就不转） |
| 投稿系统要位图 | 600 dpi PNG（从矢量 PDF 渲染，保证与 PDF 同版） |
| 导师要 Origin 格式 | `result.opju`（可编辑）+ 同名 pdf/png/tif |

## 七、与用户的交互红线（硬规则）

- **用户说"改好了让你翻译/导出"之前，绝不碰用户的 PPT/图文件**——不覆盖、不"顺手刷新"、不恢复旧版。导出覆盖论文目录文件前必须先得到明确指令。
- 用户交付 PPT 时先只读检查 + 备份副本到 image-cache，再动内容。
- 转换用 `DispatchEx`（独立进程），用户开着 PowerPoint 时**永不 Quit**、不附加其会话。
- 用户对版式的手工调整（换图、挪框）优先级高于一切已存脚本/导出物；发现文件夹版本与用户 PPT 不一致时，以用户 PPT 为准并先问再覆盖。

关联：`academic-paper`（论文流水线）；记忆 `jetson-thor-paper`（图 1–5 的实战记录与定稿状态）。
