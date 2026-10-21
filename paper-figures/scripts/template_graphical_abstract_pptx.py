# -*- coding: utf-8 -*-
"""
template_graphical_abstract_pptx.py — 可编辑视觉摘要 PPTX 模板 (基于 pptx_core)

生成全原生、可双击修改文字与图元的 PowerPoint 视觉摘要：
- Banner 版: 2.5:1 比例 (Elsevier, Springer)
- Square 版: 1:1 比例 (Cell Press, ACS)
注入 East Asian 字体声明、微圆角控制与阴影清除，用户或导师可在 Office 中自由替换模块。
"""

import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

try:
    from pptx_core import (
        apply_east_asian_font, add_run, set_round_radius, 
        remove_shadow, configure_text_frame, create_card, create_horizontal_callout
    )
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    from pptx_core import (
        apply_east_asian_font, add_run, set_round_radius, 
        remove_shadow, configure_text_frame, create_card, create_horizontal_callout
    )

def build_banner_abstract_pptx(output_pptx="graphical_abstract_banner.pptx"):
    """Elsevier 2.5:1 比例可编辑 PPTX (宽度 25cm, 高度 10cm)"""
    prs = Presentation()
    prs.slide_width = Cm(25.0)
    prs.slide_height = Cm(10.0)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    C_INPUT_BG = RGBColor(241, 245, 249)
    C_MECH_BG = RGBColor(239, 246, 255)
    C_OUT_BG = RGBColor(240, 253, 244)
    C_BORDER_BLUE = RGBColor(37, 99, 235)
    C_BORDER_GRAY = RGBColor(148, 163, 184)
    C_BORDER_GRN = RGBColor(22, 163, 74)
    C_DARK = RGBColor(30, 41, 59)
    
    # 1. 阶段 1 卡片
    create_card(slide, Cm(1.0), Cm(1.2), Cm(6.8), Cm(7.6), bg_color=C_INPUT_BG, border_color=C_BORDER_GRAY, radius_adj=3000)
    tb1 = slide.shapes.add_textbox(Cm(1.2), Cm(1.5), Cm(6.4), Cm(7.0))
    tf1 = tb1.text_frame; configure_text_frame(tf1)
    p1 = tf1.paragraphs[0]; p1.alignment = PP_ALIGN.CENTER
    add_run(p1, "1. Input / Challenge", font_name="Arial", size_pt=14.0, bold=True, color_rgb=C_DARK)
    p1_sub = tf1.add_paragraph(); p1_sub.space_before = Pt(12)
    add_run(p1_sub, "• Single-event upsets\n• High latency in orbit\n• Thermal dissipation",
            font_name="Arial", size_pt=11.5, color_rgb=RGBColor(71, 85, 105))
            
    # 2. 阶段 2 卡片 (核心高亮)
    create_card(slide, Cm(9.0), Cm(1.2), Cm(7.0), Cm(7.6), bg_color=C_MECH_BG, border_color=C_BORDER_BLUE, line_width_pt=1.5, radius_adj=3000)
    tb2 = slide.shapes.add_textbox(Cm(9.2), Cm(1.5), Cm(6.6), Cm(7.0))
    tf2 = tb2.text_frame; configure_text_frame(tf2)
    p2 = tf2.paragraphs[0]; p2.alignment = PP_ALIGN.CENTER
    add_run(p2, "2. Proposed Mechanism", font_name="Arial", size_pt=14.0, bold=True, color_rgb=C_BORDER_BLUE)
    p2_sub = tf2.add_paragraph(); p2_sub.space_before = Pt(12)
    add_run(p2_sub, "• Out-of-band power cycle\n• Dual-modular telemetry\n• Embodied self-healing",
            font_name="Arial", size_pt=11.5, color_rgb=RGBColor(30, 58, 138))
            
    # 3. 阶段 3 卡片
    create_card(slide, Cm(17.2), Cm(1.2), Cm(6.8), Cm(7.6), bg_color=C_OUT_BG, border_color=C_BORDER_GRN, line_width_pt=1.5, radius_adj=3000)
    tb3 = slide.shapes.add_textbox(Cm(17.4), Cm(1.5), Cm(6.4), Cm(7.0))
    tf3 = tb3.text_frame; configure_text_frame(tf3)
    p3 = tf3.paragraphs[0]; p3.alignment = PP_ALIGN.CENTER
    add_run(p3, "3. Key Impact", font_name="Arial", size_pt=14.0, bold=True, color_rgb=C_BORDER_GRN)
    p3_sub = tf3.add_paragraph(); p3_sub.space_before = Pt(12)
    add_run(p3_sub, "• 99.98% Reliability\n• Zero data loss\n• Rapid recovery < 10s",
            font_name="Arial", size_pt=11.5, color_rgb=RGBColor(20, 83, 45))
            
    # 0 度水平指示呼叫框 (箭头交错处)
    create_horizontal_callout(slide, Cm(7.9), Cm(4.5), Cm(1.0), Cm(0.8), "→", font_name="Arial", size_pt=14.0)
    create_horizontal_callout(slide, Cm(16.1), Cm(4.5), Cm(1.0), Cm(0.8), "→", font_name="Arial", size_pt=14.0)
    
    prs.save(output_pptx)
    print(f"[Success] Editable PPTX Graphical Abstract generated: {output_pptx}")

if __name__ == '__main__':
    build_banner_abstract_pptx()
