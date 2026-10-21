# -*- coding: utf-8 -*-
"""
color_palettes.py — 顶级学术色盲安全配色方案库 (Colorblind-Safe Palettes)

包含科学界公认的顶级色盲安全调色板：
1. Okabe-Ito 调色板 (8色，全色觉无障碍黄金标准，Nature/Science 强烈推荐)
2. Paul Tol 调色板族 (Bright, Vibrant, Muted, High-Contrast)
3. 顺序 (Sequential) 与发散 (Diverging) 配色建议

提供一键设置 matplotlib 颜色循环 (Color Cycle) 函数。
"""

from cycler import cycler
import matplotlib.pyplot as plt

# 1. Okabe & Ito (2008) 配色方案 (通用于正常色觉与红绿色盲)
OKABE_ITO = [
    "#E69F00",  # 橙色 (Orange)
    "#56B4E9",  # 天蓝 (Sky Blue)
    "#009E73",  # 蓝绿 (Bluish Green)
    "#F0E442",  # 明黄 (Yellow)
    "#0072B2",  # 深蓝 (Blue)
    "#D55E00",  # 朱红 (Vermilion)
    "#CC79A7",  # 紫红 (Reddish Purple)
    "#000000"   # 纯黑 (Black)
]

# 2. Paul Tol (2021) 调色板族
PAUL_TOL_VIBRANT = [
    "#EE7733",  # 橙
    "#0077BB",  # 蓝
    "#33BBEE",  # 青
    "#EE3377",  # 品红
    "#CC3311",  # 红
    "#009988",  # 绿
    "#BBBBBB"   # 灰
]

PAUL_TOL_MUTED = [
    "#CC6677",  # 柔粉红
    "#332288",  # 靛蓝
    "#DDCC77",  # 砂黄
    "#117733",  # 深绿
    "#88CCEE",  # 浅青
    "#882255",  # 酒红
    "#44AA99",  # 薄荷绿
    "#999933",  # 橄榄绿
    "#AA4499"   # 紫罗兰
]

PAUL_TOL_BRIGHT = [
    "#4477AA",  # 蓝
    "#66CCEE",  # 青
    "#228833",  # 绿
    "#CCBB44",  # 黄
    "#EE6677",  # 红
    "#AA3377",  # 紫
    "#BBBBBB"   # 灰
]

PAUL_TOL_HIGH_CONTRAST = [
    "#004488",  # 深蓝
    "#DDAA33",  # 金黄
    "#BB5566"   # 玫红
]

PALETTES = {
    "okabe_ito": OKABE_ITO,
    "vibrant": PAUL_TOL_VIBRANT,
    "muted": PAUL_TOL_MUTED,
    "bright": PAUL_TOL_BRIGHT,
    "high_contrast": PAUL_TOL_HIGH_CONTRAST
}

def set_academic_palette(palette_name="okabe_ito"):
    """
    一键为当前 matplotlib session 设置学术色盲安全循环配色
    """
    p_name = palette_name.lower().replace("-", "_")
    colors = PALETTES.get(p_name, OKABE_ITO)
    plt.rcParams["axes.prop_cycle"] = cycler(color=colors)
    return colors

def get_palette_colors(palette_name="okabe_ito", n=None):
    """
    获取指定配色的 HEX 色值列表
    """
    p_name = palette_name.lower().replace("-", "_")
    colors = PALETTES.get(p_name, OKABE_ITO)
    if n is not None:
        return colors[:n]
    return colors
