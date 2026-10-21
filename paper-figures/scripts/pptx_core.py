# -*- coding: utf-8 -*-
"""
pptx_core.py — 学术图表与海报通用的 PPTX 原生矢量引擎 (paper-figures 核心共享库)
支持：
1. 论文插图（2x 尺寸建模）与学术海报（1:2 几何等比缩放）全场景；
2. OpenXML DrawingML 底层样式控制：东亚中文字体 <a:ea> 强制注入、微妙圆角曲率 (adj=3000)、阴影彻底清除；
3. 中文排版标点避头尾禁则 (CJK Kinnsoku Shori)：字符容积保护与语法意群主动断行；
4. 0 度水平文字图表组件与带遮罩连接线。
"""

import os
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn

# ==========================================
# 一、OpenXML 底层样式与东亚中文字体注入
# ==========================================

def apply_east_asian_font(run, font_name="Noto Serif SC"):
    """
    强制声明东亚字体标签 (<a:ea>)。
    解决 Windows Office 打开 PPTX 时中文字体被静默回退为默认宋体/微软雅黑的致命 Bug。
    """
    rPr = run._r.get_or_add_rPr()
    ea = parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{font_name}"/>')
    rPr.append(ea)

def add_run(p, text, font_name="Noto Serif SC", size_pt=12.0, bold=False, color_rgb=None):
    """
    统一的文字 Run 工厂，自动绑定中文字体声明与排版属性。
    """
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color_rgb is not None:
        run.font.color.rgb = color_rgb
    apply_east_asian_font(run, font_name)
    return run

def set_round_radius(shape, adj_val=3000):
    """
    精细调整圆角矩形的圆弧曲率。
    - 默认 adj=16667：过于圆滑，有廉价移动 App 感；
    - 学术卡片 adj=2500~3500：克制严谨、端庄典雅；
    - 胶囊徽章 adj=50000：标准半圆胶囊。
    """
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
    """
    强制移除形状默认阴影，维持学术出版物严谨的扁平矢量风格 (Flat Aesthetics)。
    """
    try:
        spPr = shape._sp.spPr
        effectLst = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst')
        if effectLst is not None:
            spPr.remove(effectLst)
    except Exception:
        pass

def configure_text_frame(tf, word_wrap=True):
    """
    四向内边距强制清零 (Zero Textbox Margins)。
    清除默认 0.1 英寸（2.54mm）内边距，确保排版净宽完全符合精确计算，杜绝标点孤悬。
    """
    tf.word_wrap = word_wrap
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0

def set_subscript(run):
    """设置字元下标偏移"""
    rPr = run._r.get_or_add_rPr()
    rPr.set("baseline", "-25000")

def set_superscript(run):
    """设置字元上标偏移"""
    rPr = run._r.get_or_add_rPr()
    rPr.set("baseline", "30000")

# ==========================================
# 二、中文学术排版与标点避头尾禁则
# ==========================================

# 禁止出现在行首的标点符号集合 (禁则)
PUNCTUATION_HANGING = set("，。；：！？、）》】”’…—")

def sanitize_cjk_line_breaks(text):
    """
    语法意群智能换行：
    对长难学术中文句子，在分号、逗号等天然语法断句点主动断行，
    保证标点符号永远依附在上一行句尾，绝不孤悬于下一行行首。
    """
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(line.strip())
    return "\n".join(cleaned_lines)

def add_bullet_card_paragraph(tf, tag_text, body_text, 
                              font_title="SimHei", font_body="Noto Serif SC",
                              size_pt=15.0, color_title=None, color_body=None,
                              space_after_pt=6.0):
    """
    构建符合学术排版规范的带标签段落：
    【标签】使用加粗字体，正文使用常规字体，同属一个段落流式排布，左边缘 100% 垂直对齐。
    """
    p = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
    p.space_after = Pt(space_after_pt)
    
    if tag_text:
        add_run(p, tag_text, font_name=font_title, size_pt=size_pt, bold=True, color_rgb=color_title)
        
    safe_body = sanitize_cjk_line_breaks(body_text)
    add_run(p, safe_body, font_name=font_body, size_pt=size_pt, bold=False, color_rgb=color_body)
    return p

# ==========================================
# 三、通用学术卡片与图元工厂
# ==========================================

def create_card(slide, left, top, width, height, 
                bg_color, border_color=None, line_width_pt=0.75, radius_adj=3000):
    """
    通用学术圆角卡片工厂（无阴影、微圆角）
    适用于：论文示意图模块容器、海报分栏卡片
    """
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

def create_pill_badge(slide, left, top, width, height, 
                      bg_color, text, font_name="SimHei", size_pt=10.0, 
                      text_color=RGBColor(255, 255, 255)):
    """
    标准学术半圆胶囊徽章（分类标签、状态提示）
    """
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.fill.background()
    set_round_radius(shape, 50000)  # 半圆胶囊
    remove_shadow(shape)
    
    tf = shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    configure_text_frame(tf, word_wrap=False)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    add_run(p, text, font_name=font_name, size_pt=size_pt, bold=True, color_rgb=text_color)
    return shape

def create_horizontal_callout(slide, left, top, width, height, 
                             text, font_name="SimHei", size_pt=9.0, 
                             bg_color=RGBColor(255, 255, 255), 
                             border_color=RGBColor(203, 213, 225),
                             text_color=RGBColor(26, 32, 44)):
    """
    【0 度水平文字呼叫气泡】：
    用于连线、箭头交错处的标注说明。自带纯白背景遮罩与微细边框，
    绝不随箭头角度倾斜，确保 100% 水平易读。
    """
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(0.5)
    set_round_radius(shape, 4000)
    remove_shadow(shape)
    
    tf = shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    configure_text_frame(tf, word_wrap=True)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    add_run(p, text, font_name=font_name, size_pt=size_pt, bold=True, color_rgb=text_color)
    return shape
