# -*- coding: utf-8 -*-
"""
template_graphical_abstract.py — 顶级学术期刊 Graphical Abstract (视觉摘要) 矢量生成模板

支持两大行业黄金尺寸：
1. Square 版 (1:1 比例): 适配 Cell Press, ACS, RSC (1200 x 1200 px @ 300 DPI, 即 4.0 x 4.0 inch)
2. Banner 版 (2.5:1 比例): 适配 Elsevier, Springer, Nature Communications (1328 x 531 px @ 300 DPI, 即 4.43 x 1.77 inch)

视觉架构：
采用经典的三段式高冲击力科研逻辑流：
【研究痛点 / 起始输入】 ──> 【核心机制 / 创新干预】 ──> 【突破性能 / 转化应用】
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import numpy as np

# 经典学术与机制配色
COLOR_INPUT = "#E2E8F0"      # 浅灰底 (对照/输入)
COLOR_MECH = "#EFF6FF"       # 浅蓝底 (核心机制)
COLOR_OUT = "#F0FDF4"        # 浅绿底 (高性能/产出)
BORDER_INPUT = "#64748B"
BORDER_MECH = "#2563EB"
BORDER_OUT = "#16A34A"
NAVY = "#0F294A"
CHARCOAL = "#1E293B"

def draw_graphical_abstract_banner(output_path="graphical_abstract_banner.pdf"):
    """
    Elsevier 2.5:1 标准横版视觉摘要 (1328 x 531 px @ 300 DPI)
    """
    fig, ax = plt.subplots(figsize=(4.43, 1.77), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis('off')
    
    # 1. 阶段 1: 挑战与输入 (左侧卡片)
    card1 = FancyBboxPatch((3, 5), 26, 30, boxstyle="round,pad=0.2,rounding_size=2",
                           facecolor=COLOR_INPUT, edgecolor=BORDER_INPUT, lw=1.2)
    ax.add_patch(card1)
    ax.text(16, 31, "1. Input / Challenge", fontsize=7.5, fontweight='bold', color=CHARCOAL, ha='center')
    ax.text(16, 23, "• Single-event upsets\n• High latency in orbit\n• Thermal dissipation",
            fontsize=5.8, color="#334155", ha='center', va='center')
    
    # 箭头 1 -> 2
    ax.add_patch(FancyArrowPatch((30, 20), (37, 20), arrowstyle='simple,head_width=5,head_length=5',
                                 facecolor='#94A3B8', edgecolor='none'))
    
    # 2. 阶段 2: 核心机制/干预 (中间卡片，高亮)
    card2 = FancyBboxPatch((38, 5), 28, 30, boxstyle="round,pad=0.2,rounding_size=2",
                           facecolor=COLOR_MECH, edgecolor=BORDER_MECH, lw=1.5)
    ax.add_patch(card2)
    ax.text(52, 31, "2. Proposed Mechanism", fontsize=7.5, fontweight='bold', color=BORDER_MECH, ha='center')
    ax.text(52, 23, "• Out-of-band power cycle\n• Dual-modular telemetry\n• Embodied self-healing",
            fontsize=5.8, color="#1E3A8A", ha='center', va='center')
    
    # 箭头 2 -> 3
    ax.add_patch(FancyArrowPatch((67, 20), (74, 20), arrowstyle='simple,head_width=5,head_length=5',
                                 facecolor=BORDER_MECH, edgecolor='none'))
    
    # 3. 阶段 3: 突破性能与结论 (右侧卡片)
    card3 = FancyBboxPatch((75, 5), 22, 30, boxstyle="round,pad=0.2,rounding_size=2",
                           facecolor=COLOR_OUT, edgecolor=BORDER_OUT, lw=1.5)
    ax.add_patch(card3)
    ax.text(86, 31, "3. Key Impact", fontsize=7.5, fontweight='bold', color=BORDER_OUT, ha='center')
    ax.text(86, 23, "• 99.98% Reliability\n• Zero data loss\n• Rapid recovery < 10s",
            fontsize=5.8, color="#14532D", ha='center', va='center')
    
    plt.tight_layout(pad=0.02)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[Success] Graphical abstract (Banner 2.5:1) generated: {output_path}")

def draw_graphical_abstract_square(output_path="graphical_abstract_square.pdf"):
    """
    Cell Press 1:1 标准方版视觉摘要 (1200 x 1200 px @ 300 DPI, 4x4 in)
    """
    fig, ax = plt.subplots(figsize=(4.0, 4.0), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # 顶部标题横幅
    ax.text(50, 93, "In-Situ Space Radiation Self-Healing Pipeline",
            fontsize=8.5, fontweight='bold', color=NAVY, ha='center')
            
    # 上半部: 痛点与输入 (卡片 A)
    card_top = FancyBboxPatch((8, 62), 84, 25, boxstyle="round,pad=0.2,rounding_size=2",
                              facecolor=COLOR_INPUT, edgecolor=BORDER_INPUT, lw=1.2)
    ax.add_patch(card_top)
    ax.text(50, 81, "Conventional Challenge: SEU-Induced Accelerator Latchup",
            fontsize=7.0, fontweight='bold', color=CHARCOAL, ha='center')
    ax.text(50, 71, "Heavy ion beam -> CMOS latchup -> Telemetry collapse",
            fontsize=6.2, color="#475569", ha='center')
            
    # 向下箭头 (0度水平文字遮罩)
    ax.add_patch(FancyArrowPatch((50, 61), (50, 43), arrowstyle='simple,head_width=6,head_length=6',
                                 facecolor='#64748B', edgecolor='none'))
    ax.text(50, 52, "Autonomous Detection", fontsize=6.0, fontweight='bold', color="#0F172A",
            ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', pad=2))
            
    # 中下部: 创新解决机制 (卡片 B)
    card_bot = FancyBboxPatch((8, 8), 84, 33, boxstyle="round,pad=0.2,rounding_size=2",
                              facecolor=COLOR_MECH, edgecolor=BORDER_MECH, lw=1.5)
    ax.add_patch(card_bot)
    ax.text(50, 35, "Proposed Solution: Tri-Fold Orthogonal Cold-Cycle Recovery",
            fontsize=7.2, fontweight='bold', color=BORDER_MECH, ha='center')
    ax.text(50, 23, "1. In-situ telemetry threshold trigger (> 10s)\n2. Complete power rail rail-to-rail decay\n3. Autonomous re-initialization and checkpoint resume",
            fontsize=6.0, color="#1E3A8A", ha='center', va='center')
            
    plt.tight_layout(pad=0.02)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[Success] Graphical abstract (Square 1:1) generated: {output_path}")

if __name__ == '__main__':
    draw_graphical_abstract_banner()
    draw_graphical_abstract_square()
