# -*- coding: utf-8 -*-
"""
template_figure_diagram.py — 学术海报图表与概念机制图矢量绘制规范 (matplotlib)
黄金绘图准则：
1. 【0 度水平文字铁律】：任何连线、斜向箭头上的标注文字必须绝对保持 0 度水平，严禁斜体或旋转！
2. 【垂直长条文字竖排】：遇垂直长方形区块，文字以竖排字符流堆叠（'内\\n容\\n联\\n动'），绝不旋转 90 度。
3. 【文字防穿帮白色遮罩】：悬浮文字与连线交错处，必须配置白底遮罩（set_bbox / facecolor='white'）。
4. 【图内字号下限】：1:1 海报中图内文字绝对 >= 22pt，确保 1.5 米外清晰可辨。
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse, Circle, FancyBboxPatch, Polygon, FancyArrowPatch
import numpy as np

# 1. 字体与显示配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 2. 配色系统（与海报主题严格协调）
NAVY = '#0F294A'
SLATE = '#2B4C7E'
AMBER = '#C28212'
AMBER_BG = '#FFFBEB'
CARD_BG = '#FFFFFF'
CHARCOAL = '#1A202C'
LINE_GRAY = '#64748B'
OUTER_BORDER = '#94A3B8'

def draw_triangular_cycle_diagram(output_path="fig_framework_horizontal.png"):
    """
    经典正三角理论生态循环图（0度水平文字规范范例）
    """
    fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)
    ax.set_aspect('equal')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 节点坐标
    P_top = np.array([50.0, 83.0])  # 顶部维度
    P_bl = np.array([20.0, 20.0])   # 左下维度
    P_br = np.array([80.0, 20.0])   # 右下维度
    P_c = np.array([50.0, 48.0])    # 核心中心

    ew, eh = 28.0, 14.0  # 椭圆节点尺寸
    cr = 10.0           # 中心圆半径

    # 1. 绘制通往中心的虚线与 0 度水平标注文字
    # 顶部 -> 中心
    ax.plot([P_top[0], P_c[0]], [P_top[1] - eh/2, P_c[1] + cr],
            color=LINE_GRAY, linestyle='--', linewidth=2.0, zorder=2)
    # 【重点】：文字绝对 0 度水平，带白色背景遮罩，不旋转！
    ax.text(50.0, 66.5, '认知生成基础', fontsize=12.0, fontweight='bold', color=CHARCOAL,
            ha='center', va='center', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    # 左下 -> 中心 (斜线)
    ax.plot([P_bl[0] + 12, P_c[0] - 8], [P_bl[1] + 6, P_c[1] - 6],
            color=LINE_GRAY, linestyle='--', linewidth=2.0, zorder=2)
    # 【重点】：斜线上的文字依旧保持 0 度水平！
    ax.text(32.0, 39.0, '认知内化保障', fontsize=12.0, fontweight='bold', color=CHARCOAL,
            ha='center', va='center', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    # 右下 -> 中心 (斜线)
    ax.plot([P_br[0] - 12, P_c[0] + 8], [P_br[1] + 6, P_c[1] - 6],
            color=LINE_GRAY, linestyle='--', linewidth=2.0, zorder=2)
    # 【重点】：斜线上的文字保持 0 度水平！
    ax.text(68.0, 39.0, '认知深化路径', fontsize=12.0, fontweight='bold', color=CHARCOAL,
            ha='center', va='center', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    # 2. 绘制外围双向箭头与 0 度水平说明文字
    # 左斜边箭头 (P_bl <-> P_top)
    ax.annotate("", xy=(P_top[0] - 11, P_top[1] - 5), xytext=(P_bl[0] + 5, P_bl[1] + 8),
                arrowprops=dict(arrowstyle="<->", color=LINE_GRAY, lw=2.0), zorder=3)
    ax.text(25.0, 56.0, '共在性凝聚\n场域性保障', fontsize=11.5, fontweight='bold', color=CHARCOAL,
            ha='center', va='center', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    # 右斜边箭头 (P_top <-> P_br)
    ax.annotate("", xy=(P_br[0] - 5, P_br[1] + 8), xytext=(P_top[0] + 11, P_top[1] - 5),
                arrowprops=dict(arrowstyle="<->", color=LINE_GRAY, lw=2.0), zorder=3)
    ax.text(75.0, 56.0, '具身情境\n意义构建', fontsize=11.5, fontweight='bold', color=CHARCOAL,
            ha='center', va='center', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    # 底部横向箭头 (P_bl <-> P_br)
    ax.annotate("", xy=(P_br[0] - 15, P_bl[1]), xytext=(P_bl[0] + 15, P_bl[1]),
                arrowprops=dict(arrowstyle="<->", color=LINE_GRAY, lw=2.0), zorder=3)
    ax.text(50.0, P_bl[1] - 4.5, '整合性实践能力 / 主体性驱动', fontsize=11.5, fontweight='bold', color=CHARCOAL,
            ha='center', va='top', zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', pad=2))

    # 3. 绘制外围三个节点（优雅椭圆）
    nodes = [
        (P_top[0], P_top[1], "空间社群", SLATE),
        (P_bl[0], P_bl[1], "组织治理", SLATE),
        (P_br[0], P_br[1], "课程教学", SLATE)
    ]
    for x, y, label, col in nodes:
        ell = Ellipse((x, y), width=ew, height=eh, facecolor='#F0F7FF', edgecolor=col, linewidth=2.4, zorder=4)
        ax.add_patch(ell)
        ax.text(x, y, label, fontsize=15.0, fontweight='bold', color=NAVY, ha='center', va='center', zorder=5)

    # 4. 绘制中心高亮节点（琥珀金核心圆形）
    c_center = Circle((P_c[0], P_c[1]), radius=cr, facecolor=AMBER_BG, edgecolor=AMBER, linewidth=3.0, zorder=6)
    ax.add_patch(c_center)
    ax.text(P_c[0], P_c[1] + 2.2, "科技与人文", fontsize=12.5, fontweight='bold', color=AMBER, ha='center', va='center', zorder=7)
    ax.text(P_c[0], P_c[1] - 3.2, "协同", fontsize=14.0, fontweight='bold', color=AMBER, ha='center', va='center', zorder=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
    plt.close()
    print(f"Figure generated successfully: {output_path}")

if __name__ == '__main__':
    draw_triangular_cycle_diagram()
