# -*- coding: utf-8 -*-
"""
journal_profiles.py — 顶级国际学术期刊尺寸、版面与字体规范预设矩阵

覆盖顶刊家族：
1. Nature Portfolio (Nature, Nature Communications, etc.)
2. Science (AAAS, Science Advances, etc.)
3. Cell Press (Cell, Molecular Cell, etc.)
4. IEEE Transactions & Conferences
5. Elsevier Journals

核心功能：
- 自动换算毫米 (mm) 与英寸 (inch)，保证精确匹配最终出版栏宽；
- 统一配置 plt.rcParams（字体、刻度朝向、线宽、无衬线字体标准）；
- 自动锚定符合期刊规范的子图编号 (a, b 或 A, B)。
"""

import matplotlib.pyplot as plt

MM_TO_INCH = 1.0 / 25.4

# 顶刊物理栏宽规范 (单位: mm)
JOURNAL_SPECS = {
    "nature": {
        "name": "Nature Portfolio",
        "single_mm": 89.0,
        "double_mm": 183.0,
        "one_half_mm": 136.0,
        "max_height_mm": 240.0,
        "font_family": "sans-serif",
        "font_name": ["Arial", "Helvetica", "DejaVu Sans"],
        "base_font_pt": 7.0,
        "min_font_pt": 5.0,
        "label_case": "lower",      # (a), (b), (c)
        "label_bold": True,
        "label_format": "({label})"
    },
    "science": {
        "name": "Science (AAAS)",
        "single_mm": 55.0,
        "double_mm": 174.0,
        "one_half_mm": 120.0,
        "max_height_mm": 230.0,
        "font_family": "sans-serif",
        "font_name": ["Helvetica", "Arial", "DejaVu Sans"],
        "base_font_pt": 7.5,
        "min_font_pt": 6.0,
        "label_case": "upper",      # (A), (B), (C)
        "label_bold": True,
        "label_format": "({label})"
    },
    "cell": {
        "name": "Cell Press",
        "single_mm": 85.0,
        "double_mm": 174.0,
        "one_half_mm": 130.0,
        "max_height_mm": 235.0,
        "font_family": "sans-serif",
        "font_name": ["Arial", "Helvetica", "DejaVu Sans"],
        "base_font_pt": 7.0,
        "min_font_pt": 6.0,
        "label_case": "upper",      # (A), (B), (C)
        "label_bold": True,
        "label_format": "{label}"
    },
    "ieee": {
        "name": "IEEE Transactions & Conferences",
        "single_mm": 88.9,          # 3.5 in
        "double_mm": 181.9,         # 7.16 in
        "one_half_mm": 135.0,
        "max_height_mm": 240.0,
        "font_family": "sans-serif",
        "font_name": ["Times New Roman", "Arial", "DejaVu Sans"],
        "base_font_pt": 8.0,
        "min_font_pt": 6.0,
        "label_case": "lower",      # (a), (b), (c)
        "label_bold": True,
        "label_format": "({label})"
    },
    "elsevier": {
        "name": "Elsevier Standard",
        "single_mm": 90.0,
        "double_mm": 190.0,
        "one_half_mm": 140.0,
        "max_height_mm": 240.0,
        "font_family": "sans-serif",
        "font_name": ["Arial", "Helvetica", "DejaVu Sans"],
        "base_font_pt": 7.5,
        "min_font_pt": 6.0,
        "label_case": "upper",      # (A), (B), (C)
        "label_bold": True,
        "label_format": "({label})"
    }
}

def get_journal_figsize(journal="nature", columns="single", aspect_ratio=0.75):
    """
    计算精准符合期刊出版宽度的 figure figsize (英寸)
    columns: 'single' (单栏), 'double' (通栏/双栏), '1.5' (一栏半)
    aspect_ratio: 高度 / 宽度
    """
    j = journal.lower()
    spec = JOURNAL_SPECS.get(j, JOURNAL_SPECS["nature"])
    
    if columns == "double":
        width_mm = spec["double_mm"]
    elif columns in ("1.5", "one_half"):
        width_mm = spec["one_half_mm"]
    else:
        width_mm = spec["single_mm"]
        
    width_in = width_mm * MM_TO_INCH
    height_in = width_in * aspect_ratio
    return (width_in, height_in)

def apply_journal_style(journal="nature"):
    """
    一键配置顶级期刊全局绘图样式规范
    """
    j = journal.lower()
    spec = JOURNAL_SPECS.get(j, JOURNAL_SPECS["nature"])
    
    rc_params = {
        # 字体与排版
        "font.family": spec["font_family"],
        "font.sans-serif": spec["font_name"],
        "font.size": spec["base_font_pt"],
        "axes.titlesize": spec["base_font_pt"] + 1.0,
        "axes.labelsize": spec["base_font_pt"],
        "xtick.labelsize": spec["min_font_pt"],
        "ytick.labelsize": spec["min_font_pt"],
        "legend.fontsize": spec["min_font_pt"],
        
        # 轴线与刻度（刻度向内，边框清晰）
        "axes.linewidth": 0.6,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "lines.linewidth": 1.0,
        "lines.markersize": 4.0,
        
        # 矢量字体兼容性（禁用 Type 3 位图，强制 TrueType 轮廓）
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        
        # 留白极小化
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "savefig.dpi": 300
    }
    plt.rcParams.update(rc_params)
    return spec

def add_panel_label(ax, label="a", journal="nature", x_offset=-0.12, y_offset=1.05):
    """
    为子图添加符合期刊出版标准的子图标号 (如 a, b 或 A, B)
    自动处理大小写与括号规范，左上角防重叠锚定
    """
    j = journal.lower()
    spec = JOURNAL_SPECS.get(j, JOURNAL_SPECS["nature"])
    
    clean_l = label.strip("()")
    if spec["label_case"] == "upper":
        clean_l = clean_l.upper()
    else:
        clean_l = clean_l.lower()
        
    formatted_text = spec["label_format"].format(label=clean_l)
    
    ax.text(x_offset, y_offset, formatted_text,
            transform=ax.transAxes,
            fontsize=spec["base_font_pt"] + 1.5,
            fontweight="bold" if spec["label_bold"] else "normal",
            va="top", ha="right", zorder=10)
