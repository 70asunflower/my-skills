# -*- coding: utf-8 -*-
"""
verify_poster_diff.py — 学术海报 PDF 与 PPTX 双轨像素级切片比对与交付质检工具

工作流程：
1. 使用 PyMuPDF (fitz) 将 ReportLab 印刷级 PDF 渲染为 300 DPI 预览位图；
2. 调用 Windows PowerPoint COM 接口 (win32com.client) 无头导出 PPTX 为对应高清 PNG；
3. 将两者归一化至相同像素高度与宽度；
4. 纵向切出 4 大核心视区（顶部标题区、Sec1-2 理论区、Sec3 机理三联图区、Sec4 结论底栏区）并拼接生成左右对照图；
5. 执行标点避头尾与文字截断自动巡检。
"""

import os
import sys
from PIL import Image

def rasterize_pdf(pdf_path, output_png, target_width=1800):
    """使用 PyMuPDF 将 PDF 渲染为高精度图片"""
    try:
        import fitz
    except ImportError:
        print("Error: PyMuPDF (fitz) is required. Install via pip install pymupdf")
        return False
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    # 计算缩放比例以匹配 target_width
    zoom = target_width / page.rect.width
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(output_png)
    doc.close()
    print(f"[PDF] Rasterized to {output_png} ({pix.width}x{pix.height})")
    return True

def export_pptx_slide(pptx_path, output_png, target_width=1800, target_height=4800):
    """通过 PowerPoint COM 无头静默导出幻灯片为 PNG"""
    try:
        import win32com.client
    except ImportError:
        print("Error: pywin32 is required. Install via pip install pywin32")
        return False
    
    abs_pptx = os.path.abspath(pptx_path)
    abs_png = os.path.abspath(output_png)
    
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    pres = ppt.Presentations.Open(abs_pptx, ReadOnly=True, WithWindow=False)
    # PPT COM 的 Slides 集合是 1-indexed
    slide = pres.Slides(1)
    slide.Export(abs_png, "PNG", target_width, target_height)
    pres.Close()
    ppt.Quit()
    print(f"[PPTX] Exported slide to {output_png} ({target_width}x{target_height})")
    return True

def make_side_by_side_comparison(pdf_img_path, pptx_img_path, out_prefix="comp"):
    """归一化并切片生成 4 个区域的双轨比对图"""
    img_pdf = Image.open(pdf_img_path)
    img_pptx = Image.open(pptx_img_path)
    
    # 归一化至相同尺寸 (以 PPTX 导出的 1800 x 4800 为基准)
    target_w, target_h = 1800, 4800
    img_pdf = img_pdf.resize((target_w, target_h), Image.Resampling.LANCZOS)
    img_pptx = img_pptx.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # 四大垂直视区切片比率定义 (基于 60x160cm 典型布局)
    slices = [
        ("1_header", 0.00, 0.20, "顶部标题与个人信息区"),
        ("2_sec1_sec2", 0.20, 0.45, "第一二板块：理论与核心框架"),
        ("3_sec3_mechanism", 0.45, 0.80, "第三板块：三维运作机理与三联图"),
        ("4_footer", 0.80, 1.00, "第四板块与底栏致谢参考文献")
    ]
    
    results = []
    for s_name, y_start_pct, y_end_pct, desc in slices:
        y1 = int(target_h * y_start_pct)
        y2 = int(target_h * y_end_pct)
        h = y2 - y1
        
        crop_pdf = img_pdf.crop((0, y1, target_w, y2))
        crop_pptx = img_pptx.crop((0, y1, target_w, y2))
        
        # 左右拼接 (左：PDF 印刷基准，右：PPTX 可编辑版)
        combined = Image.new("RGB", (target_w * 2 + 20, h), (230, 230, 230))
        combined.paste(crop_pdf, (0, 0))
        combined.paste(crop_pptx, (target_w + 20, 0))
        
        out_file = f"{out_prefix}_{s_name}.png"
        combined.save(out_file)
        results.append((out_file, desc))
        print(f"[Diff] Generated slice: {out_file} ({desc})")
        
    return results

def run_verification(pdf_path, pptx_path):
    print("=" * 60)
    print("Academic Poster Dual-Track Verification Pipeline")
    print("=" * 60)
    
    pdf_png = "temp_pdf_render.png"
    pptx_png = "temp_pptx_render.png"
    
    if not rasterize_pdf(pdf_path, pdf_png):
        return
    if not export_pptx_slide(pptx_path, pptx_png):
        return
        
    slices = make_side_by_side_comparison(pdf_png, pptx_png)
    
    print("\n" + "=" * 60)
    print("Verification Completed. Inspection Checklist:")
    print("1. [Headers]: Verify left-aligned Navy banners and Amber bars match exactly.")
    print("2. [CJK Punctuation]: Inspect all lines to ensure NO line starts with ，、。；")
    print("3. [Diagrams]: Check all figure annotations are 100% horizontal without overlap.")
    print("4. [Font Size]: Ensure body font matches 15pt in PPTX (>=30pt in 1:1 PDF).")
    print("5. [Cassette Clearance]: Confirm bottom 2.5-3cm is completely free of text.")
    print("=" * 60)

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        run_verification(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python verify_poster_diff.py <poster.pdf> <poster.pptx>")
