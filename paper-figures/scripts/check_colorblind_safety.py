# -*- coding: utf-8 -*-
"""
check_colorblind_safety.py — 色盲友好与灰度打印安全自动质检工具

解决的核心痛点：
Nature, Science, IEEE 严格要求插图对于色觉障碍读者（尤其是占男性约 8% 的红绿色盲人群）
具备良好的可辨识度，同时在纯黑白灰度打印下曲线、散点与色块不得混淆粘连。

工作流程：
1. 输入 PDF 或 PNG/JPG 图片（若为 PDF，使用 PyMuPDF 自动转为高精度位图）；
2. 基于生理学颜色感知模型 (Machado et al. 2009)，在线性 RGB 空间内精确仿真：
   - 绿色盲 (Deuteranopia - 最常见红绿色盲)
   - 红色盲 (Protanopia - 红色敏感度缺失)
   - 灰度黑白打印 (Grayscale Print Simulation)
3. 自动生成 4 联对比质检审计大图 `*_cvd_audit.png`；
4. 输出审计报告与配色优化建议。
"""

import os
import sys
import numpy as np
from PIL import Image

# Machado et al. (2009) 100% 严重度变换矩阵 (线性 RGB)
# 绿盲 (Deuteranopia)
M_DEUTERANOPIA = np.array([
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501,  0.047413],
    [-0.011820, 0.042940, 0.968881]
])

# 红盲 (Protanopia)
M_PROTANOPIA = np.array([
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281,  0.099216],
    [-0.003882, -0.048116, 1.051998]
])

# 灰度加权系数 (ITU-R BT.601)
M_GRAYSCALE = np.array([
    [0.299, 0.587, 0.114],
    [0.299, 0.587, 0.114],
    [0.299, 0.587, 0.114]
])

def srgb_to_linear(rgb):
    """sRGB 空间伽马逆校正转为线性 RGB"""
    rgb = rgb.astype(np.float32) / 255.0
    mask = rgb <= 0.04045
    linear = np.empty_like(rgb)
    linear[mask] = rgb[mask] / 12.92
    linear[~mask] = ((rgb[~mask] + 0.055) / 1.055) ** 2.4
    return linear

def linear_to_srgb(linear):
    """线性 RGB 重新进行伽马校正转回 sRGB"""
    linear = np.clip(linear, 0.0, 1.0)
    mask = linear <= 0.0031308
    srgb = np.empty_like(linear)
    srgb[mask] = linear[mask] * 12.92
    srgb[~mask] = 1.055 * (linear[~mask] ** (1.0 / 2.4)) - 0.055
    srgb = np.clip(srgb * 255.0, 0, 255).astype(np.uint8)
    return srgb

def simulate_cvd(img_rgb, matrix):
    """应用 3x3 矩阵仿真色觉障碍"""
    linear = srgb_to_linear(img_rgb)
    # 矩阵乘法: (H, W, 3) @ M.T
    sim_linear = linear @ matrix.T
    return linear_to_srgb(sim_linear)

def render_pdf_if_needed(file_path):
    """如果是 PDF，则渲染为 PNG"""
    if file_path.lower().endswith('.pdf'):
        try:
            import fitz
        except ImportError:
            print("[Error] 需要安装 PyMuPDF: pip install pymupdf")
            return None
        doc = fitz.open(file_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=300)
        tmp_png = file_path + ".tmp_render.png"
        pix.save(tmp_png)
        doc.close()
        return tmp_png
    return file_path

def add_banner_to_image(img_arr, title_text, is_pass=True):
    """为各个子视角上方添加专业质检标头"""
    from PIL import ImageDraw, ImageFont
    im = Image.fromarray(img_arr)
    banner_h = 45
    new_im = Image.new("RGB", (im.width, im.height + banner_h), (245, 247, 250))
    draw = ImageDraw.Draw(new_im)
    
    # 绘制顶部状态条
    bar_color = (27, 54, 93) if is_pass else (194, 130, 18)
    draw.rectangle([0, 0, im.width, banner_h], fill=(235, 240, 245))
    draw.rectangle([0, banner_h - 2, im.width, banner_h], fill=bar_color)
    
    # 绘制标题文字
    draw.text((15, 12), title_text, fill=(20, 30, 45))
    new_im.paste(im, (0, banner_h))
    return np.array(new_im)

def run_colorblind_audit(input_file, output_audit_png=None):
    """执行完整的色觉安全性与灰度仿真质检"""
    print("=" * 65)
    print("  Paper-Figures: 色盲友好与灰度印刷仿真安全质检")
    print("=" * 65)
    
    actual_img_path = render_pdf_if_needed(input_file)
    if not actual_img_path or not os.path.exists(actual_img_path):
        print(f"[Error] 无法读取文件: {input_file}")
        return False
        
    im_orig = Image.open(actual_img_path).convert("RGB")
    
    # 如果临时生成了渲染文件，清理掉
    if actual_img_path != input_file and os.path.exists(actual_img_path):
        os.remove(actual_img_path)
        
    arr_orig = np.array(im_orig)
    
    # 1. 绿盲仿真 (Deuteranopia)
    arr_deut = simulate_cvd(arr_orig, M_DEUTERANOPIA)
    # 2. 红盲仿真 (Protanopia)
    arr_prot = simulate_cvd(arr_orig, M_PROTANOPIA)
    # 3. 灰度黑白打印仿真 (Grayscale)
    arr_gray = simulate_cvd(arr_orig, M_GRAYSCALE)
    
    # 添加标头
    b_orig = add_banner_to_image(arr_orig, "1. Original Figure (原始全彩 sRGB)")
    b_deut = add_banner_to_image(arr_deut, "2. Deuteranopia Simulation (绿色盲仿真，占男性约 6%)")
    b_prot = add_banner_to_image(arr_prot, "3. Protanopia Simulation (红色盲仿真，占男性约 2%)")
    b_gray = add_banner_to_image(arr_gray, "4. Grayscale Print Simulation (纯黑白印刷反差测试)")
    
    # 2x2 拼版组合
    row1 = np.hstack([b_orig, b_deut])
    row2 = np.hstack([b_prot, b_gray])
    composite = np.vstack([row1, row2])
    
    if output_audit_png is None:
        stem = os.path.splitext(input_file)[0]
        output_audit_png = f"{stem}_cvd_audit.png"
        
    final_img = Image.fromarray(composite)
    final_img.save(output_audit_png, dpi=(300, 300))
    print(f"[Success] 四联色觉质检图已生成: {output_audit_png}")
    
    print("\n" + "=" * 65)
    print("  色觉无障碍审查要点 (CVD Safety Checklist)")
    print("=" * 65)
    print("  1. 【红绿区分度】：检查面板 2 和 3 中，原本代表不同对比组的红线与绿线是否融为同一种黄褐色；")
    print("  2. 【灰度反差】：检查面板 4 中，黑白打印时相邻色块或曲线能否通过灰阶深度/明度清晰区分；")
    print("  3. 【辅助冗余编码】：强烈建议不要单靠颜色区分数据组，应叠加形状 (圆/方/三角) 或虚实线型；")
    print("  4. 【推荐安全调色板】：若发现混淆，请直接采用 Okabe-Ito 配色或 Paul Tol 配色。")
    print("=" * 65)
    return True

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        out = sys.argv[2] if len(sys.argv) > 2 else None
        run_colorblind_audit(sys.argv[1], out)
    else:
        print("用法: python check_colorblind_safety.py <figure.pdf|figure.png> [output_audit.png]")
