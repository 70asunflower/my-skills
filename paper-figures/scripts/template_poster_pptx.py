# -*- coding: utf-8 -*-
"""
template_poster_pptx.py — 可编辑学术海报 PPTX 生成器模板 (python-pptx)
- 尺寸：30 cm x 80 cm（严格 1:2 对应 60 cm x 160 cm 易拉宝，规避 Office 56 英寸限制）
- 矢量：全原生 PPT 形状与文本框，100% 可在 PowerPoint 中二次修改
- 特性：OpenXML 注入东亚中文字体声明、细微圆角曲率控制、阴影彻底移除、四向内边距归零
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml

# 1. 经典学术色彩体系 (对应 CMYK 配色)
C_PRIMARY = RGBColor(15, 41, 74)     # #0F294A 学院深蓝
C_ACCENT = RGBColor(194, 130, 18)    # #C28212 暖琥珀金
C_SLATE = RGBColor(43, 76, 126)      # #2B4C7E 板岩蓝
C_TEXT_MAIN = RGBColor(26, 32, 44)   # #1A202C 正文炭黑
C_TEXT_MUTED = RGBColor(51, 65, 85)  # #334155 次级灰色
C_BG_CARD = RGBColor(248, 250, 252)  # #F8FAFC 浅灰白卡片底
C_BORDER = RGBColor(203, 213, 225)   # #CBD5E1 微细边框
C_WHITE = RGBColor(255, 255, 255)
C_INFO_BG = RGBColor(254, 252, 247)  # #FEFCF7 暖米色

# 2. OpenXML 关键底层控制函数
def apply_east_asian_font(run, font_name="Noto Serif SC"):
    """强制声明东亚字体标签，确保中文在任何系统 PowerPoint 中正确显示"""
    rPr = run._r.get_or_add_rPr()
    ea = parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{font_name}"/>')
    rPr.append(ea)

def add_run(p, text, font_name="Noto Serif SC", size_pt=15.0, bold=False, color_rgb=C_TEXT_MAIN):
    """统一文字 Run 工厂，自带东亚字体标签注入"""
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.color.rgb = color_rgb
    apply_east_asian_font(run, font_name)
    return run

def set_round_radius(shape, adj_val=3000):
    """微调圆角曲率（默认 adj=16667 过圆，改为 3000 展现优雅学术质感）"""
    try:
        spPr = shape._sp.spPr
        prstGeom = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom')
        if prstGeom is not None:
            avLst = prstGeom.find('{http://schemas.openxmlformats.org/drawingml/2006/main}avLst')
            if avLst is not None:
                avLst.clear()
                gd = parse_xml(f'<a:gd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="adj" fmla="val {adj_val}"/>')
                avLst.append(gd)
    except Exception:
        pass

def remove_shadow(shape):
    """强制移除 PPT 默认阴影，维持扁平学术风"""
    try:
        spPr = shape._sp.spPr
        effectLst = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst')
        if effectLst is not None:
            spPr.remove(effectLst)
    except Exception:
        pass

def configure_text_frame(tf, word_wrap=True):
    """清零文本框边距，防止排版宽度被隐式内边距吞噬引发错误折行"""
    tf.word_wrap = word_wrap
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0

# 3. 核心排版组件
def create_card(slide, left, top, width, height, bg_color=C_BG_CARD, border_color=C_BORDER, line_width_pt=0.75, radius_adj=3000):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(line_width_pt)
    else:
        shape.line.fill.background()
    set_round_radius(shape, radius_adj)
    remove_shadow(shape)
    return shape

def create_section_header(slide, left, top, width, height, title):
    """
    一级标题横幅：深蓝底框 + 左侧暖琥珀金装饰竖条 + 22.5pt 粗黑体（1:1 下为 45pt）
    """
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_PRIMARY
    bar.line.fill.background()
    set_round_radius(bar, 3000)
    remove_shadow(bar)
    
    # 左侧金条
    accent = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Pt(5), top + Pt(5), Pt(6), height - Pt(10))
    accent.fill.solid()
    accent.fill.fore_color.rgb = C_ACCENT
    accent.line.fill.background()
    set_round_radius(accent, 4000)
    remove_shadow(accent)
    
    # 标题文字框
    tb = slide.shapes.add_textbox(left + Pt(19), top, width - Pt(25), height)
    tf = tb.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    configure_text_frame(tf, word_wrap=False)
    p = tf.paragraphs[0]
    add_run(p, title, font_name="SimHei", size_pt=22.5, bold=True, color_rgb=C_WHITE)
    return top + height

# 4. 主构建流程
def build_poster_pptx(output_pptx="academic_poster_30x80cm.pptx"):
    prs = Presentation()
    # 严格 1:2 画布尺寸
    prs.slide_width = Cm(30)
    prs.slide_height = Cm(80)
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白版式
    
    # 安全区定义 (两侧各留 1.0cm 安全边距)
    SAFE_LEFT = Cm(1.0)
    SAFE_WIDTH = Cm(28.0)
    
    cur_y = Cm(1.0)
    
    # --- 顶部标题区 ---
    # 主标题 (32pt, 居中)
    tb_title = slide.shapes.add_textbox(SAFE_LEFT, cur_y, SAFE_WIDTH, Cm(2.2))
    tf_t = tb_title.text_frame
    configure_text_frame(tf_t)
    p1 = tf_t.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    add_run(p1, "论文主标题第一行：核心概念与对象", font_name="SimHei", size_pt=32.0, bold=True, color_rgb=C_PRIMARY)
    
    p2 = tf_t.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    add_run(p2, "论文主标题第二行：机制探索与协同路径", font_name="SimHei", size_pt=32.0, bold=True, color_rgb=C_PRIMARY)
    cur_y += Cm(2.4)
    
    # 副标题 (23pt, 居中)
    tb_sub = slide.shapes.add_textbox(SAFE_LEFT, cur_y, SAFE_WIDTH, Cm(1.0))
    tf_s = tb_sub.text_frame
    configure_text_frame(tf_s)
    p_s = tf_s.paragraphs[0]
    p_s.alignment = PP_ALIGN.CENTER
    add_run(p_s, "——基于某理论视角的实证分析", font_name="SimHei", size_pt=23.0, bold=True, color_rgb=C_PRIMARY)
    cur_y += Cm(1.3)
    
    # 个人信息卡片
    info_h = Cm(2.4)
    create_card(slide, SAFE_LEFT, cur_y, SAFE_WIDTH, info_h, bg_color=C_INFO_BG, border_color=C_ACCENT, radius_adj=3000)
    tb_info = slide.shapes.add_textbox(SAFE_LEFT + Cm(0.5), cur_y + Cm(0.2), SAFE_WIDTH - Cm(1.0), info_h)
    tf_i = tb_info.text_frame
    configure_text_frame(tf_i)
    
    p_i1 = tf_i.paragraphs[0]
    add_run(p_i1, "作者：", font_name="SimHei", size_pt=14.5, bold=True, color_rgb=C_TEXT_MAIN)
    add_run(p_i1, "张三，李四*（通讯作者）", font_name="Noto Serif SC", size_pt=14.5, color_rgb=C_TEXT_MAIN)
    
    p_i2 = tf_i.add_paragraph()
    add_run(p_i2, "单位：", font_name="SimHei", size_pt=14.5, bold=True, color_rgb=C_TEXT_MAIN)
    add_run(p_i2, "某某大学某某学院", font_name="Noto Serif SC", size_pt=14.5, color_rgb=C_TEXT_MAIN)
    cur_y += info_h + Cm(0.5)
    
    # 一级标题示例
    cur_y = create_section_header(slide, SAFE_LEFT, cur_y, SAFE_WIDTH, Cm(1.2), "一、研究背景与理论透镜")
    cur_y += Cm(0.4)
    
    prs.save(output_pptx)
    print(f"Successfully generated {output_pptx}")

if __name__ == '__main__':
    build_poster_pptx()
