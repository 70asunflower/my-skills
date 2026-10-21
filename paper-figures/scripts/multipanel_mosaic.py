# -*- coding: utf-8 -*-
"""
multipanel_mosaic.py — 顶级期刊多子图统一拼版中枢 (Multi-Panel Mosaic Engine)

解决的核心痛点：
顶级期刊（Nature、Science、IEEE）的 Figure 1 往往由 3~6 个不同类型的子图组合而成：
(a) 概念架构/装置图；(b) 实验瞬态遥测数据；(c) 跨组别统计柱状图；(d) 性能热力图。
科研人员在 Illustrator 或 PPT 里手工拼接时，各子图字号不齐、标号歪斜、图例分散。

功能特性：
1. 基于 Matplotlib 的 `subplot_mosaic` ASCII 字符排版语法，所见即所得定义子图网格；
2. 深度联动 `journal_profiles`，自动根据目标期刊（Nature/Science/IEEE）和栏宽（单栏/双栏）计算绝对精确尺寸；
3. 全自动注入标准子图标号 (a, b 或 A, B)，外加防重叠安全边距；
4. 支持全局共享统一图例 (Global Shared Legend)。
"""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np

# 导入同目录下的期刊规范与配色库
try:
    from journal_profiles import apply_journal_style, get_journal_figsize, add_panel_label
    from color_palettes import set_academic_palette, OKABE_ITO
except ImportError:
    # 允许从外部或技能路径直接执行
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    from journal_profiles import apply_journal_style, get_journal_figsize, add_panel_label
    from color_palettes import set_academic_palette, OKABE_ITO

def create_multipanel_figure(mosaic_layout, journal="nature", columns="double", 
                            aspect_ratio=0.70, auto_label=True):
    """
    根据 ASCII 字符网格一键构建顶刊多子图画布
    mosaic_layout: 多行字符串，如：
        '''
        AAB
        AAC
        DDE
        '''
    columns: 'single' (单栏), 'double' (双栏通栏), '1.5' (一栏半)
    """
    # 1. 应用期刊排版参数与色盲安全配色
    apply_journal_style(journal)
    set_academic_palette("okabe_ito")
    
    # 2. 精确计算出版物理画幅 (英寸)
    figsize = get_journal_figsize(journal=journal, columns=columns, aspect_ratio=aspect_ratio)
    
    # 3. 创建子图马赛克
    fig, axd = plt.subplot_mosaic(mosaic_layout, figsize=figsize)
    
    # 4. 自动为每个有唯一标识的面板添加标号
    if auto_label:
        # 获取所有非空键列表（按首次出现顺序）
        unique_keys = []
        for line in mosaic_layout.strip().split("\n"):
            for ch in line.strip():
                if ch.isalnum() and ch not in unique_keys:
                    unique_keys.append(ch)
                    
        # 字母标号映射表: 0->a, 1->b, ...
        for idx, key in enumerate(unique_keys):
            if key in axd:
                panel_char = chr(ord('a') + idx)
                add_panel_label(axd[key], label=panel_char, journal=journal)
                
    return fig, axd

def demo_nature_composite_figure(output_path="fig_multipanel_demo.pdf"):
    """
    演示范例：构建典型的 Nature Double-Column 复合大图 (Figure 1)
    - A (大块): 实验架构/工作流示意图
    - B: 瞬态时间序列折线
    - C: 组间对比与统计散点
    - D (底部通栏): 跨模态性能对比条形图
    """
    layout = """
        AAB
        AAC
        DDD
    """
    fig, axd = create_multipanel_figure(layout, journal="nature", columns="double", aspect_ratio=0.68)
    
    # --- Panel A: 示意图占位 ---
    axd['A'].text(0.5, 0.5, "Panel A: Experimental Workflow\n& In-Situ Setup Diagram",
                 ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1B365D")
    axd['A'].set_facecolor("#F8FAFC")
    axd['A'].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    
    # --- Panel B: 瞬态时间序列折线 ---
    t = np.linspace(0, 10, 100)
    axd['B'].plot(t, np.sin(t) * 1.5 + 2.0, color=OKABE_ITO[0], label="Active State", lw=1.2)
    axd['B'].plot(t, np.cos(t) * 0.8 + 1.2, color=OKABE_ITO[1], label="Baseline", lw=1.2, linestyle="--")
    axd['B'].set_xlabel("Time (s)")
    axd['B'].set_ylabel("Telemetry Current (A)")
    axd['B'].legend(frameon=False, loc="upper right")
    
    # --- Panel C: 组间对比散点 ---
    np.random.seed(42)
    g1 = np.random.normal(15, 2, 20)
    g2 = np.random.normal(25, 3, 20)
    axd['C'].boxplot([g1, g2], widths=0.4, patch_artist=True,
                     boxprops=dict(facecolor="#E2E8F0", color="#475569"),
                     medianprops=dict(color="#0F294A", lw=1.5))
    # 叠加真实散点数据 (Show the Raw Data)
    axd['C'].scatter([1]*20 + np.random.normal(0, 0.04, 20), g1, color=OKABE_ITO[4], alpha=0.7, s=12)
    axd['C'].scatter([2]*20 + np.random.normal(0, 0.04, 20), g2, color=OKABE_ITO[5], alpha=0.7, s=12)
    axd['C'].set_xticklabels(["Control", "Treated"])
    axd['C'].set_ylabel("Efficiency Score (%)")
    
    # --- Panel D: 横向条形图 ---
    categories = ["Model-A", "Model-B", "Model-C", "Proposed"]
    scores = [68, 74, 82, 95]
    colors = ["#94A3B8", "#94A3B8", "#94A3B8", OKABE_ITO[0]]
    axd['D'].bar(categories, scores, color=colors, width=0.5)
    axd['D'].set_ylabel("Reliability (%)")
    axd['D'].set_ylim(0, 110)
    for idx, v in enumerate(scores):
        axd['D'].text(idx, v + 2, f"{v}%", ha="center", va="bottom", fontsize=6.5, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[Success] Multi-panel figure generated: {output_path}")

if __name__ == '__main__':
    demo_nature_composite_figure()
