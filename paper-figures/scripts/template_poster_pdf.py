# -*- coding: utf-8 -*-
"""
template_poster_pdf.py — 学术易拉宝海报印刷级 PDF 生成器模板 (ReportLab)
- 尺寸：60.6 cm x 160.6 cm（成品 60 cm x 160 cm，四边含 3mm 印刷出血）
- 色彩：CMYK 印刷模式，支持高精度矢量文字与矢量/高清插图
- 安全框：四边内缩 2cm 安全边距，底部预留 5.5-6.2cm 机械卷轴保护区
- 字体：SimHei（标题）+ NotoSerifSC（正文 >= 30pt）
"""

import os
from reportlab.lib.colors import CMYKColor
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

# 1. 物理画布与几何参数（硬性标准）
PAGE_WIDTH = 60.6 * cm      # 1717.8 pt
PAGE_HEIGHT = 160.6 * cm    # 4552.4 pt
BLEED = 0.3 * cm            # 8.5 pt (3mm 出血)
SAFE_MARGIN = 2.0 * cm      # 56.7 pt (20mm 安全边距)

TRIM_X1 = BLEED
TRIM_Y1 = BLEED
TRIM_X2 = PAGE_WIDTH - BLEED
TRIM_Y2 = PAGE_HEIGHT - BLEED

CONTENT_X1 = TRIM_X1 + SAFE_MARGIN
CONTENT_X2 = TRIM_X2 - SAFE_MARGIN
CONTENT_WIDTH = CONTENT_X2 - CONTENT_X1  # 约 56.0 cm
CONTENT_Y1 = TRIM_Y1 + SAFE_MARGIN + 55  # 底部卷轴机械留白 (~6cm)

# 2. 印刷级 CMYK 色彩定义
C_PRIMARY = CMYKColor(0.95, 0.75, 0.25, 0.35)   # 学院深蓝 (#0F294A)
C_ACCENT = CMYKColor(0.12, 0.40, 0.95, 0.05)    # 暖琥珀金 (#C28212)
C_SLATE = CMYKColor(0.80, 0.50, 0.20, 0.10)     # 板岩蓝 (#2B4C7E)
C_TEXT = CMYKColor(0.10, 0.10, 0.10, 0.95)      # 正文炭黑 (#1A1A1A)
C_CARD_BG = CMYKColor(0.01, 0.01, 0.02, 0.01)   # 卡片极浅灰白 (#F8FAFC)
C_BORDER = CMYKColor(0.15, 0.10, 0.05, 0.10)    # 边框灰 (#CBD5E1)
C_INFO_BG = CMYKColor(0.02, 0.03, 0.07, 0.00)   # 暖米色 (#FEFCF7)
C_WHITE = CMYKColor(0, 0, 0, 0)

# 3. 注册本地中文字体
def register_fonts():
    font_paths = [
        ('SimHei', ['C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyh.ttc']),
        ('NotoSerifSC', ['C:/Windows/Fonts/NotoSerifSC-VF.ttf', 'C:/Windows/Fonts/simsun.ttc'])
    ]
    for font_name, paths in font_paths:
        for p in paths:
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont(font_name, p))
                pdfmetrics.registerFontFamily(font_name, normal=font_name, bold=font_name)
                break

register_fonts()

# 4. 专业印刷裁切角线 (Crop Marks)
def draw_crop_marks(c):
    c.saveState()
    c.setStrokeColor(CMYKColor(0, 0, 0, 1))
    c.setLineWidth(0.6)
    mark_len = 20
    # 左下
    c.line(TRIM_X1 - mark_len, TRIM_Y1, TRIM_X1 - 2, TRIM_Y1)
    c.line(TRIM_X1, TRIM_Y1 - mark_len, TRIM_X1, TRIM_Y1 - 2)
    # 右下
    c.line(TRIM_X2 + 2, TRIM_Y1, TRIM_X2 + mark_len, TRIM_Y1)
    c.line(TRIM_X2, TRIM_Y1 - mark_len, TRIM_X2, TRIM_Y1 - 2)
    # 左上
    c.line(TRIM_X1 - mark_len, TRIM_Y2, TRIM_X1 - 2, TRIM_Y2)
    c.line(TRIM_X1, TRIM_Y2 + 2, TRIM_X1, TRIM_Y2 + mark_len)
    # 右上
    c.line(TRIM_X2 + 2, TRIM_Y2, TRIM_X2 + mark_len, TRIM_Y2)
    c.line(TRIM_X2, TRIM_Y2 + 2, TRIM_X2, TRIM_Y2 + mark_len)
    c.restoreState()

# 5. 基础组件：圆角卡片
def draw_card(c, x, y, w, h, bg_color=C_CARD_BG, border_color=C_BORDER, radius=12, fill=True, stroke=True):
    c.saveState()
    if fill:
        c.setFillColor(bg_color)
    if stroke:
        c.setStrokeColor(border_color)
        c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, radius, fill=1 if fill else 0, stroke=1 if stroke else 0)
    c.restoreState()

# 6. 基础组件：一级标题通栏横幅
def draw_section_header(c, x, y, title, width=CONTENT_WIDTH, height=68):
    c.saveState()
    # 深蓝主底框
    c.setFillColor(C_PRIMARY)
    c.roundRect(x, y - height, width, height, 8, fill=1, stroke=0)
    # 左侧琥珀金装饰条
    c.setFillColor(C_ACCENT)
    c.roundRect(x + 10, y - height + 10, 12, height - 20, 4, fill=1, stroke=0)
    # 横幅文字（白字，黑体 45pt）
    c.setFillColor(C_WHITE)
    c.setFont('SimHei', 45)
    c.drawString(x + 38, y - height + 18, title)
    c.restoreState()
    return y - height - 20  # 返回下一模块可用起始 y

# 7. 主构建流程框架
def build_pdf_poster(output_pdf="academic_poster_60x160cm.pdf"):
    c = canvas.Canvas(output_pdf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    
    # 填充全局背景色
    c.setFillColor(C_WHITE)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # 绘制裁切线
    draw_crop_marks(c)
    
    cur_y = TRIM_Y2 - SAFE_MARGIN
    
    # --- 顶部标题与个人信息区 ---
    # 论坛顶标
    c.setFillColor(C_PRIMARY)
    c.setFont('SimHei', 28)
    c.drawString(CONTENT_X1, cur_y - 30, "高等教育综合改革与拔尖创新人才培养专题论坛 · 学术成果展示")
    cur_y -= 80
    
    # 主标题（双行平衡，64pt 加粗居中）
    c.setFillColor(C_PRIMARY)
    c.setFont('SimHei', 64)
    c.drawCentredString(PAGE_WIDTH / 2.0, cur_y, "论文主标题第一行：核心概念与对象")
    cur_y -= 78
    c.drawCentredString(PAGE_WIDTH / 2.0, cur_y, "论文主标题第二行：机制探索与协同路径")
    cur_y -= 62
    
    # 副标题（46pt 居中）
    c.setFont('SimHei', 46)
    c.drawCentredString(PAGE_WIDTH / 2.0, cur_y, "——基于某理论视角的实证分析")
    cur_y -= 50
    
    # 个人信息框（暖米色底、双细线边框）
    info_h = 135
    draw_card(c, CONTENT_X1, cur_y - info_h, CONTENT_WIDTH, info_h, bg_color=C_INFO_BG, border_color=C_ACCENT, radius=8)
    # 信息内文字 (思源宋体 30pt)
    c.setFillColor(C_TEXT)
    c.setFont('SimHei', 30)
    c.drawString(CONTENT_X1 + 25, cur_y - 45, "作者：张三，李四*（通讯作者）")
    c.drawString(CONTENT_X1 + 25, cur_y - 85, "单位：某某大学某某学院")
    c.drawString(CONTENT_X1 + 25, cur_y - 125, "邮箱：contact@university.edu.cn")
    cur_y -= (info_h + 30)
    
    # --- 各板块示例 ---
    cur_y = draw_section_header(c, CONTENT_X1, cur_y, "一、研究背景与理论透镜")
    
    # 保存并生成 PDF
    c.showPage()
    c.save()
    print(f"Successfully generated {output_pdf}")

if __name__ == '__main__':
    build_pdf_poster()
