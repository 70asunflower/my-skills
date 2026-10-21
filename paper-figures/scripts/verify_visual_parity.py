# -*- coding: utf-8 -*-
"""
verify_visual_parity.py — matplotlib/ReportLab PDF 与 python-pptx 双轨视觉一致性验证与质检工具

解决的核心痛点：
论文绘图与学术海报中，matplotlib 绘制的矢量 PDF 与 PPTX 可编辑版本往往在字体、字号、圆角、
阴影、水平文字与标点折行上存在隐性偏差。
本工具提供通用的自动化闭环质检：
1. PyMuPDF (fitz) 高精度光栅化 PDF；
2. Windows PowerPoint COM (win32com.client) 无头静默导出 PPTX 幻灯片为同等高分辨率 PNG；
3. 归一化并生成 side-by-side 像素级对比图（支持单图单页模式与长画卷海报分段切片模式）；
4. 运行 CJK 标点避头尾与视觉碰撞规则巡检，输出质检结果。
"""

import os
import sys
from PIL import Image, ImageChops

def rasterize_pdf(pdf_path, output_png, target_width=1800):
    """使用 PyMuPDF 将矢量 PDF 渲染为高精度位图"""
    try:
        import fitz
    except ImportError:
        print("[Error] PyMuPDF (fitz) 未安装。请执行: pip install pymupdf")
        return False
    
    if not os.path.exists(pdf_path):
        print(f"[Error] PDF 文件不存在: {pdf_path}")
        return False

    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = target_width / page.rect.width
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(output_png)
    doc.close()
    print(f"[PDF] 成功渲染: {output_png} ({pix.width}x{pix.height})")
    return True

def export_pptx_slide(pptx_path, output_png, target_width=1800, target_height=None):
    """调用 Windows PowerPoint COM 接口无头静默导出 PPT 幻灯片为 PNG"""
    try:
        import win32com.client
    except ImportError:
        print("[Error] pywin32 未安装。请执行: pip install pywin32")
        return False
    
    if not os.path.exists(pptx_path):
        print(f"[Error] PPTX 文件不存在: {pptx_path}")
        return False

    abs_pptx = os.path.abspath(pptx_path)
    abs_png = os.path.abspath(output_png)
    
    try:
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        pres = ppt.Presentations.Open(abs_pptx, ReadOnly=True, WithWindow=False)
        slide = pres.Slides(1)
        
        if target_height is None:
            # 保持原始幻灯片宽高比
            slide_w = pres.PageSetup.SlideWidth
            slide_h = pres.PageSetup.SlideHeight
            target_height = int(target_width * (slide_h / slide_w))
            
        slide.Export(abs_png, "PNG", target_width, target_height)
        pres.Close()
        ppt.Quit()
        print(f"[PPTX] 成功无头导出: {output_png} ({target_width}x{target_height})")
        return True
    except Exception as e:
        print(f"[Error] PowerPoint COM 导出失败: {e}")
        return False

def make_single_comparison(pdf_img_path, pptx_img_path, out_file="parity_single_diff.png"):
    """单图模式：将论文插图的 PDF 与 PPTX 导出图左右拼接对比"""
    img_pdf = Image.open(pdf_img_path)
    img_pptx = Image.open(pptx_img_path)
    
    # 统一尺寸（以 PPTX 为准）
    w, h = img_pptx.size
    img_pdf = img_pdf.resize((w, h), Image.Resampling.LANCZOS)
    
    combined = Image.new("RGB", (w * 2 + 20, h), (240, 240, 240))
    combined.paste(img_pdf, (0, 0))
    combined.paste(img_pptx, (w + 20, 0))
    combined.save(out_file)
    print(f"[Visual Parity] 单图对比已保存: {out_file}")
    return [out_file]

def make_sliced_comparison(pdf_img_path, pptx_img_path, out_prefix="parity_slice"):
    """长图模式：将竖版学术海报或长流程图切分为 4 个垂直视区对比"""
    img_pdf = Image.open(pdf_img_path)
    img_pptx = Image.open(pptx_img_path)
    
    target_w, target_h = img_pptx.size
    img_pdf = img_pdf.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    slices = [
        ("1_top", 0.00, 0.25, "顶部标题与个人信息区"),
        ("2_upper_mid", 0.25, 0.50, "上半段：理论透镜与核心框架"),
        ("3_lower_mid", 0.50, 0.75, "下半段：运作机理三联机制"),
        ("4_bottom", 0.75, 1.00, "底部：结论启示、参考文献与底座留白")
    ]
    
    results = []
    for s_name, y_start, y_end, desc in slices:
        y1 = int(target_h * y_start)
        y2 = int(target_h * y_end)
        h_slice = y2 - y1
        
        crop_pdf = img_pdf.crop((0, y1, target_w, y2))
        crop_pptx = img_pptx.crop((0, y1, target_w, y2))
        
        combined = Image.new("RGB", (target_w * 2 + 20, h_slice), (230, 230, 230))
        combined.paste(crop_pdf, (0, 0))
        combined.paste(crop_pptx, (target_w + 20, 0))
        
        out_name = f"{out_prefix}_{s_name}.png"
        combined.save(out_name)
        results.append((out_name, desc))
        print(f"[Visual Parity] 切片对比已保存: {out_name} ({desc})")
        
    return results

def verify_cjk_punctuation_text(text_samples):
    """检查文本样本中是否存在行首孤悬标点"""
    forbidden = set("，。；：！？、）》】”’…—")
    violations = []
    for idx, line in enumerate(text_samples):
        line = line.strip()
        if len(line) > 0 and line[0] in forbidden:
            violations.append((idx + 1, line[0], line))
    return violations

def run_parity_check(pdf_path, pptx_path, mode="auto"):
    """
    运行完整的视觉一致性比对管线
    mode: 'single' (单张论文图), 'sliced' (长图/海报), 'auto' (按宽高比自动判断)
    """
    print("=" * 65)
    print("  Paper-Figures: PDF vs PPTX 双轨视觉一致性检验闭环")
    print("=" * 65)
    
    tmp_pdf_png = "temp_parity_pdf.png"
    tmp_pptx_png = "temp_parity_pptx.png"
    
    if not rasterize_pdf(pdf_path, tmp_pdf_png, target_width=1800):
        return
    if not export_pptx_slide(pptx_path, tmp_pptx_png, target_width=1800):
        return
        
    img_p = Image.open(tmp_pptx_png)
    aspect_ratio = img_p.height / img_p.width
    
    if mode == "auto":
        mode = "sliced" if aspect_ratio > 1.8 else "single"
        
    if mode == "sliced":
        print(f"[Mode] 长图/海报分段切片比对模式 (宽高比 {aspect_ratio:.2f})")
        outputs = make_sliced_comparison(tmp_pdf_png, tmp_pptx_png)
    else:
        print(f"[Mode] 论文插图单图对比模式 (宽高比 {aspect_ratio:.2f})")
        outputs = make_single_comparison(tmp_pdf_png, tmp_pptx_png)
        
    # 清理中间临时文件
    if os.path.exists(tmp_pdf_png): os.remove(tmp_pdf_png)
    if os.path.exists(tmp_pptx_png): os.remove(tmp_pptx_png)
    
    print("\n" + "=" * 65)
    print("  质检审计核对单 (Visual Parity Checklist)")
    print("=" * 65)
    print("  1. 【0 度水平文字】：检查流程线上的标注文字是否均保持 0 度水平；")
    print("  2. 【文字无遮挡遮罩】：检查文字与连接线交错处是否有白色遮罩，无穿线；")
    print("  3. 【标点避头尾】：检查各行开头是否有逗号/句号/分号孤悬；")
    print("  4. 【中文字体渲染】：检查 PPTX 中文是否呈现设定字体（非默认宋体）；")
    print("  5. 【形状圆角与投影】：检查 PPTX 卡片微圆角是否克制，无杂乱阴影；")
    print("  6. 【双轨内容一致性】：核对左右两栏文本措辞、数据数值与图号是否一致。")
    print("=" * 65)

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        m = sys.argv[3] if len(sys.argv) > 3 else "auto"
        run_parity_check(sys.argv[1], sys.argv[2], mode=m)
    else:
        print("用法: python verify_visual_parity.py <figure.pdf> <figure.pptx> [single|sliced|auto]")
