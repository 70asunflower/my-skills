# -*- coding: utf-8 -*-
"""IEEE paper figure template (matplotlib) — paper-figures skill.

Copy this file per figure (e.g. plot_fig3_xxx.py in the project workdir),
fill the DATA / AXES sections, and it exports PDF+PNG(600dpi) straight
into the paper figure folder. Conventions and hard-won pitfalls are marked
with !! where they bit us before."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# ---- 0. output location & naming (paper-figures skill conventions) ----
# 定稿目录 = 论文文件夹\figure\；命名 fig<N>_<slug>（N=论文图号）；
# 备选/rebuttal 素材用 fig_backup_<slug>；草稿绝不放 figure 目录。
# 脚本本身放项目工作区（可重跑直出 figure 目录）。
OUTDIR = r"D:\MyData\ZL\论文\2026 International Conference on Satellite Computing (Satellite)\figure"
NAME = "figN_slug"

matplotlib.rcParams.update({
    "font.family": ["Times New Roman", "Arial"],   # 与正文一致;无衬线图用 Arial 打头
    "mathtext.fontset": "dejavusans",              # 行内粗体/下标与正文同族
    "axes.unicode_minus": False,
    "font.size": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6,
    "xtick.direction": "in", "ytick.direction": "in",
    "xtick.top": True, "ytick.right": True,
    "pdf.fonttype": 42, "ps.fonttype": 42,         # TrueType 内嵌(LaTeX 可用)
})

# ---- 1. 数据纪律（硬约束） ----
# !! 只画真实数据：禁止插值/平滑/重采样瞬态过程。
# !! 图上标注的每个数值必须回查原始数据逐点核对后再标。
# !! 时间戳带 +08:00 -> .replace(tzinfo=None)。
# !! 相对时间轴用"当日秒数"，不要用 naive datetime 的 .timestamp()
#    （Windows 会按本地时区解释，整体错位几小时）：
# def sod(t): return (t - t.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

# DATA = ...  # 读原始 jsonl/csv，构建 (t_rel, value) 序列

# ---- 2. 版面：跨双栏 7.16 in / 单栏 3.5 in；高按内容 2.4-4.5 ----
FIG_W, FIG_H = 7.16, 3.5
fig = plt.figure(figsize=(FIG_W, FIG_H))
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.28,
                      left=0.09, right=0.91, top=0.95, bottom=0.12)

ax = fig.add_subplot(gs[0])
# AXES = ...  # ax.plot(...); 断轴压缩用"分段映射 X(t) + // 断点符号"
# ax.set_xlim(...); ax.xaxis.set_major_locator(MultipleLocator(...))
# !! 轴标注防碰撞：数值/文本标注写完后逐个 zoom 自查，或交 visual-judge 验收
# !! 双 Y 轴 (twinx) 会盖住 inset/标注 -> ax.set_zorder(axV.get_zorder()+1); ax.patch.set_visible(False)

# ---- 2.5 坐标画布（人机定位语言，详见 SKILL.md §一·五） ----
# 迭代期内所有会调位置的文本/箭头经 Canvas 注册，出图附带 *_grid.png + *_layout.txt，
# 用户照网格报坐标（"把 t_xxx 移到 (0.42, 0.35)"）即改即重跑，定位不走截图。
#   import sys; sys.path.insert(0, r"C:/Users/qilin/.zcode/skills/paper-figures/scripts")
#   from canvas import Canvas
#   c = Canvas(fig, default_ax=ax)
#   c.text("t_note1", 0.42, 0.35, "48 MeV", coord="fig", fontsize=8)
#   c.arrow("ar1", (0.30, 0.50), (0.20, 0.60), coord="fig",
#           arrowprops=dict(arrowstyle="->", lw=0.6))
#   c.save(os.path.join(OUTDIR, NAME))   # -> .pdf/.png + _grid.png + _layout.txt
# 注意: 经 Canvas 放置的元素不要再传 transform/xycoords; 碰撞报告在 _layout.txt 末尾。

# ---- 3. 导出：矢量 PDF + 600dpi PNG，同名三件套（SVG 不用：pdfLaTeX 不直接支持） ----
# !! 白边最小化（用户硬偏好）：一律 bbox_inches="tight" + 发丝级 pad（0.02 in）
for ext, kw in (("pdf", {}), ("png", {"dpi": 600})):
    kw.update(bbox_inches="tight", pad_inches=0.02)
    fig.savefig(os.path.join(OUTDIR, f"{NAME}.{ext}"), **kw)
plt.close(fig)

# ---- 4. 图注素材：<NAME>_notes.txt（事件时刻表/数据依据/口径边界） ----
with open(os.path.join(OUTDIR, f"{NAME}_notes.txt"), "w", encoding="utf-8") as f:
    f.write(f"Notes for {NAME}.\n")
    f.write("绝对时刻映射 / 各标注的数据依据 / 被图形省略的细节 / 诚实边界。\n")
print("saved", NAME, "->", OUTDIR)
