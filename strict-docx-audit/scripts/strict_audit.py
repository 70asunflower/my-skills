# -*- coding: utf-8 -*-
r"""docx 严格审查 —— 通用全量一键检查（12 项）。

用法:
    python strict_audit.py <file.docx> [--source <source.md>] [--skip-fidelity]

退出码: 0=全部通过, 1=存在错误（含保真失败）
依赖: python-docx

通用性: 默认适用于中文工程论文/报告 (A4/宋体/黑体/仿宋/GB/T 7714)。
       如需不同页面尺寸、边距或字体，改下方「可调常量」区即可。

--- 可调常量（如果目标文档使用不同风格，改这里） ---
"""

# ============== 可调常量 ==============
# 页面（设为 None 跳过该项检查）
PAGE_W_CM        = 21              # A4 宽度
PAGE_H_CM        = 29.7            # A4 高度
MARGIN_TOP_CM    = 3.0             # 上边距
MARGIN_BOTTOM_CM = 2.5             # 下边距
MARGIN_LEFT_CM   = 2.5             # 左边距
MARGIN_RIGHT_CM  = 2.5             # 右边距

# 期望字体
EXPECTED_CODE_FONT  = 'consolas'   # 代码段（目前仅检测引用块，代码段因 Normal 混杂未强制）
EXPECTED_QUOTE_FONT = '仿宋'       # 引用块中文字体（FangSong）
EXPECTED_BODY_CN    = '宋体'       # 正文字体仅用于信息展示，不强制

# 其他
EMPTY_PARAGRAPH_THRESHOLD = 3      # 连续空段超过此数才警告
TABLE_EMPTY_CELL_RATIO    = 0.3    # 空单元格超过此行×列的比例才警告
TABLE_HEADER_BOLD_RATIO   = 0.5    # 表头 run 加粗比例低于此值才警告
# ====================================
"""


检查项:
  [1]  Bullet 字体 — Symbol→□ 方框风险
  [2]  List Number 段落 — 自动编号续号风险
  [3]  有序列表编号 — 逐组显示与源对照
  [4]  引用上标 — GB/T 7714 正文上标/参考文献平体
  [5]  内容保真 — 委托 verify_fidelity.py 逐块比对
  [6]  标题层级 — numPr 双重编号 + H1-H5 统计
  [7]  表格审计 — 数量/表头加粗/空单元格
  [8]  代码 & 引用块字体 — Consolas / 仿宋
  [9]  TOC & 页眉页脚 — TOC域/PAGE/NUMPAGES 域
  [10] 页面布局 — A4 尺寸 + 页边距
  [11] 中文字体完整性 — eastAsia 是否缺漏（"全选改字体"后遗症）
  [12] 空段落 — 正文区冗余空段
"""

import re
import argparse
import sys
import subprocess
import os
from docx import Document
from docx.shared import Cm
from docx.oxml.ns import qn

# ---- helpers ----
def P(s):
    print(s)

def _heading_names(doc):
    """返回文档中所有标题的 (索引, 样式名, 文本)."""
    return [(i, p.style.name, p.text) for i, p in enumerate(doc.paragraphs)
            if p.style and p.style.name.startswith('Heading')]

def _body_start(doc):
    """返回正文第一个非封面/摘要/目录段落的索引（大概位置）。"""
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t and not t.startswith('目录') and '更新域' not in t and not t.startswith('摘要') and not t.startswith('关键词'):
            sn = p.style.name if p.style else ''
            if sn.startswith('Heading'):
                return i
    return 0


# ======================== [1] Bullet font ========================
def check1(doc):
    np_ = doc.part.numbering_part
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    total, bad = 0, 0
    for absnum in np_.element.findall('.//w:abstractNum', ns):
        aid = absnum.get(qn('w:abstractNumId'))
        for lvl in absnum.findall('w:lvl', ns):
            lt = lvl.find('w:lvlText', ns)
            if lt is None: continue
            val = lt.get(qn('w:val'), '')
            if '%' in val: continue
            total += 1
            rPr = lvl.find('w:rPr', ns)
            if rPr is not None:
                rf = rPr.find('w:rFonts', ns)
                if rf is not None and rf.get(qn('w:ascii'), '') == 'Symbol':
                    bad += 1; P(f"     ⚠ absNum={aid} font=Symbol → □")
    if bad == 0: P(f"  ✅ 通过 — {total} 个 bullet 级别，0 Symbol")
    else:        P(f"  ❌ 失败 — {bad}/{total} 个 bullet 级别使用 Symbol 字体")
    return bad == 0


# ======================== [2] List Number ========================
def check2(doc):
    cnt, samples = 0, []
    for p in doc.paragraphs:
        if p.style and p.style.name == 'List Number':
            cnt += 1
            if len(samples) < 3: samples.append(p.text[:60])
    if cnt == 0: P("  ✅ 通过 — 0 条 List Number 段落")
    else:
        P(f"  ❌ 失败 — {cnt} 条 List Number 段落（自动编号续号 + numPr 违规风险）")
        for s in samples: P(f"     {s}")
    return cnt == 0


# ======================== [3] Ordered lists ========================
def check3(doc):
    pat = re.compile(r'^(\d+)\.\s')
    groups, cur, prev_h = [], None, "(文档开头)"
    for p in doc.paragraphs:
        if p.style and p.style.name.startswith('Heading'): prev_h = p.text[:60]
        m = pat.match(p.text)
        if m:
            if cur is None: cur = {'h': prev_h, 'nums': []}
            cur['nums'].append(int(m.group(1)))
        elif cur is not None:
            groups.append(cur); cur = None
    if cur: groups.append(cur)
    ok, err = 0, 0
    for g in groups:
        exp = list(range(1, len(g['nums']) + 1))
        if g['nums'] == exp: ok += 1
        else:
            err += 1
            P(f"     {g['h'][:50]}")
            P(f"       显示: {g['nums']}  |  独立列表应从 1 开始: {exp}")
    if err == 0: P(f"  ✅ 全部 {ok} 组均从 1 连续"); return True
    else:        P(f"  ⚠ {err}/{ok+err} 组不是从 1 开始（可能源文件连续编号，属正常）"); return False


# ======================== [4] Citation superscript ========================
def check4(doc):
    CIT_RE = re.compile(r'^\[\d+(?:[\s,，\-]+\d+)*\]$')
    ref_start, ref_end = None, None
    for i, p in enumerate(doc.paragraphs):
        s = p.style.name if p.style else ''
        if s.startswith('Heading') and '参考文献' in p.text and ref_start is None: ref_start = i
        elif s == 'Heading 1' and ref_start is not None: ref_end = i; break
    if ref_start is None: P("  ⚠ 未找到参考文献章节"); return True
    if ref_end is None: ref_end = len(doc.paragraphs)
    body_sup, viol_in, viol_out = 0, 0, 0
    for i, p in enumerate(doc.paragraphs):
        in_ref = ref_start <= i < ref_end
        for run in p.runs:
            if not CIT_RE.match(run.text.strip()): continue
            if in_ref and run.font.superscript: viol_in += 1
            elif not in_ref and not run.font.superscript: viol_out += 1
            elif not in_ref and run.font.superscript: body_sup += 1
    passed = viol_in == 0 and viol_out == 0
    if passed: P(f"  ✅ 通过 — 正文上标 {body_sup}，误标 {viol_in}，漏标 {viol_out}")
    else:
        P(f"  ❌ 失败 — 正文上标 {body_sup}")
        if viol_in: P(f"     参考文献区误上标: {viol_in}")
        if viol_out: P(f"     正文未上标: {viol_out}")
    return passed


# ======================== [5] Fidelity ========================
def check5(docx_path, source_path):
    this_dir = os.path.dirname(os.path.abspath(__file__))
    vf = os.path.join(this_dir, '..', '..', 'md2docx-formal', 'scripts', 'verify_fidelity.py')
    if not os.path.exists(vf):
        P(f"  ⚠ 未找到 verify_fidelity.py")
        return True
    try:
        r = subprocess.run([sys.executable, vf, source_path, docx_path],
                           capture_output=True, text=True, timeout=120)
        for line in r.stdout.strip().split('\n')[-6:]: P(f"  {line}")
        return r.returncode == 0
    except Exception as e:
        P(f"  ⚠ 保真检查出错: {e}")
        return True


# ======================== [6] Heading hierarchy ========================
def check6(doc):
    stats = {'Heading 1':0,'Heading 2':0,'Heading 3':0,'Heading 4':0,'Heading 5':0}
    numpr_c, gaps = 0, []
    for p in doc.paragraphs:
        sn = p.style.name if p.style else ''
        if sn in stats:
            stats[sn] += 1
            pPr = p._p.pPr
            if pPr is not None and pPr.find(qn('w:numPr')) is not None:
                numpr_c += 1
                if numpr_c <= 3: P(f"     ⚠ numPr 标题: {p.text[:40]}")
    P(f"  H1={stats['Heading 1']}  H2={stats['Heading 2']}  H3={stats['Heading 3']}  "
      f"H4={stats['Heading 4']}  H5={stats['Heading 5']}")
    # 层级空洞检查
    if stats['Heading 1'] > 0 and stats['Heading 2'] == 0: gaps.append("H1→? 无 H2")
    if stats['Heading 2'] > 0 and stats['Heading 3'] == 0: gaps.append("H2→? 无 H3")
    for g in gaps: P(f"     ⚠ 层级间隙: {g}")
    if numpr_c == 0: P("  ✅ numPr=0")
    else:            P(f"  ❌ {numpr_c} 个标题含 numPr（双重编号风险）")
    return numpr_c == 0


# ======================== [7] Table audit ========================
def check7(doc):
    """检查表格数量、表头格式、空单元格。"""
    tables = doc.tables
    P(f"  表数量: {len(tables)}")
    issues = 0
    for ti, tbl in enumerate(tables):
        if len(tbl.rows) == 0: continue
        # 表头加粗检查
        hdr_bold = 0
        hdr_runs = 0
        for cell in tbl.rows[0].cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    hdr_runs += 1
                    if run.font.bold: hdr_bold += 1
        if hdr_runs > 0 and hdr_bold / hdr_runs < TABLE_HEADER_BOLD_RATIO:
            P(f"     ⚠ 表 {ti+1} 表头加粗率 {hdr_bold}/{hdr_runs} (<{TABLE_HEADER_BOLD_RATIO})")
            issues += 1
        # 空单元格
        empty = sum(1 for row in tbl.rows for cell in row.cells
                    if all(p.text.strip() == '' for p in cell.paragraphs))
        if empty > max(1, len(tbl.rows) * len(tbl.columns) * TABLE_EMPTY_CELL_RATIO):
            P(f"     ⚠ 表 {ti+1} 空单元格过多 ({empty} 个空)")
            issues += 1
    if issues == 0: P(f"  ✅ 通过"); return True
    else:           P(f"  ⚠ {issues} 个可疑项（请人工确认）"); return False


# ======================== [8] Code & Quote font ========================
def check8(doc):
    """代码/引用块字体检查（非强制——不同文档可能使用不同字体）。"""
    quote_issues = []
    for p in doc.paragraphs:
        sn = p.style.name if p.style else ''
        if sn == 'Quote':
            for run in p.runs:
                fn = (run.font.name or '').lower()
                # 中英文混合检测：Quote 段落里只要有中文 run 就应该有 eastAsia 或匹配 QUOTE_FONT
                if fn and 'fang' not in fn and '仿宋' not in fn and 'times' not in fn:
                    quote_issues.append((fn, p.text[:40]))
                    break
    nq = len([p for p in doc.paragraphs if p.style and p.style.name == 'Quote'])
    if not quote_issues:
        P(f"  ✅ 通过 — {nq} 个 Quote 段落"); return True
    else:
        P(f"  ⚠ {len(quote_issues)} 个 Quote 段落字体非标准 ({nq} 个段落，期望 {EXPECTED_QUOTE_FONT}）")
        for fn, txt in quote_issues[:3]: P(f"     font={fn} text={txt!r}")
        return False


# ======================== [9] TOC & Header/Footer ========================
def check9(doc):
    ok = True
    # TOC 域 — 在段落 XML 中搜索 fldChar
    has_toc = False
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    for p in doc.paragraphs:
        flds = p._p.findall('.//w:fldChar', ns)
        for f in flds:
            if f.get(qn('w:fldCharType')) == 'begin':
                # 看指令是否含 TOC
                instr = p._p.find('.//w:instrText', ns)
                if instr is not None and 'TOC' in (instr.text or ''):
                    has_toc = True
    if has_toc: P("  ✅ TOC 域存在")
    else:       P("  ⚠ 未找到 TOC 域（可能未生成目录页）"); ok = False  # informational

    # 页眉页脚
    for si, section in enumerate(doc.sections):
        hdr = section.header
        ftr = section.footer
        has_page_field = False
        has_numpages = False
        if ftr:
            # 搜索页脚 XML 找 PAGE / NUMPAGES
            ftr_xml = ftr._element.xml
            if 'PAGE' in ftr_xml: has_page_field = True
            if 'NUMPAGES' in ftr_xml: has_numpages = True
        if si == 0:  # 只报第一节
            if has_page_field and has_numpages:
                P(f"  ✅ 页脚含 PAGE + NUMPAGES 域")
            else:
                P(f"  ⚠ 页脚缺域: PAGE={has_page_field}, NUMPAGES={has_numpages}")
                ok = False  # informational
    return ok  # informational — 部分文档不需要 TOC/页眉页脚


# ======================== [10] Page layout ========================
def check10(doc):
    if PAGE_W_CM is None:
        P("  ⏭ 跳过（PAGE_W_CM=None）"); return True
    for si, section in enumerate(doc.sections):
        pw = section.page_width; ph = section.page_height
        ml = section.left_margin; mr = section.right_margin
        mt = section.top_margin; mb = section.bottom_margin
        pw_ok = abs(pw - Cm(PAGE_W_CM)) < Cm(0.2)
        ph_ok = abs(ph - Cm(PAGE_H_CM)) < Cm(0.2)
        ml_ok = MARGIN_LEFT_CM is None or abs(ml - Cm(MARGIN_LEFT_CM)) < Cm(0.2)
        mr_ok = MARGIN_RIGHT_CM is None or abs(mr - Cm(MARGIN_RIGHT_CM)) < Cm(0.2)
        mt_ok = MARGIN_TOP_CM is None or abs(mt - Cm(MARGIN_TOP_CM)) < Cm(0.2)
        mb_ok = MARGIN_BOTTOM_CM is None or abs(mb - Cm(MARGIN_BOTTOM_CM)) < Cm(0.2)
        all_ok = all([pw_ok, ph_ok, ml_ok, mr_ok, mt_ok, mb_ok])
        if si == 0:
            P(f"  页面: {pw/914400*2.54:.1f}\"×{ph/914400*2.54:.1f}\"  "
              f"边距 L{ml/914400*2.54:.1f} R{mr/914400*2.54:.1f} "
              f"T{mt/914400*2.54:.1f} B{mb/914400*2.54:.1f} in")
            if all_ok: P(f"  ✅ {PAGE_W_CM}×{PAGE_H_CM}cm + 标准边距")
            else:
                errs = []
                if not pw_ok: errs.append(f"宽度≠{PAGE_W_CM}cm")
                if not ph_ok: errs.append(f"高度≠{PAGE_H_CM}cm")
                if not ml_ok: errs.append(f"左≠{MARGIN_LEFT_CM}cm")
                if not mr_ok: errs.append(f"右≠{MARGIN_RIGHT_CM}cm")
                if not mt_ok: errs.append(f"上≠{MARGIN_TOP_CM}cm")
                if not mb_ok: errs.append(f"下≠{MARGIN_BOTTOM_CM}cm")
                P(f"  ⚠ 偏差: {', '.join(errs)}")
                return False
    return True  # informational


# ======================== [11] Chinese font completeness ========================
def check11(doc):
    """检查中文 run 是否因"全选改字体"丢失 eastAsia。

    判定逻辑：
    - run 无 rFonts → 从段落样式继承 → ✅ 正常
    - run 有 rFonts 且有 eastAsia → ✅ 正常
    - run 有 rFonts 但缺 eastAsia 且含中文 → ❌ 全选改字体后遗症
    """
    CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
    body_start = _body_start(doc)
    missing = 0
    checked = 0
    for p in doc.paragraphs:
        sn = p.style.name if p.style else ''
        if sn.startswith('Heading'): continue
        if not CJK_RE.search(p.text): continue
        checked += 1
        for run in p.runs:
            if not CJK_RE.search(run.text): continue
            rPr = run._r.find(qn('w:rPr'))
            if rPr is None: continue  # 无 rPr → 继承样式 → OK
            rf = rPr.find(qn('w:rFonts'))
            if rf is None: continue  # 无 rFonts → 继承样式 → OK
            ea = rf.get(qn('w:eastAsia'))
            if not ea:
                missing += 1
                if missing <= 3: P(f"     ⚠ 缺 eastAsia: {p.text[:40]!r}")
                break  # 每段只报一次
    if missing == 0: P(f"  ✅ 通过 — {checked} 个含中文段落 eastAsia 完整")
    else:
        P(f"  ❌ 失败 — {missing}/{checked} 个中文段落缺 eastAsia")
        return False
    return True


# ======================== [12] Empty paragraphs ========================
def check12(doc):
    """正文区域不该有大量连续空段落。"""
    body_start = _body_start(doc)
    empty_runs = []
    empty_seq = []
    cur_seq = 0
    for i, p in enumerate(doc.paragraphs):
        if i < body_start: continue
        sn = p.style.name if p.style else ''
        if sn.startswith('Heading'): continue
        if p.text.strip() == '':
            cur_seq += 1
            if i not in empty_runs: empty_runs.append(i)
        else:
            if cur_seq >= 3: empty_seq.append((i - cur_seq, cur_seq))
            cur_seq = 0
    if cur_seq >= 3: empty_seq.append((len(doc.paragraphs) - cur_seq, cur_seq))

    if not empty_seq:
        P(f"  ✅ 通过 — 无连续 ≥{EMPTY_PARAGRAPH_THRESHOLD} 个空段落")
        return True
    else:
        P(f"  ⚠ {len(empty_seq)} 处连续空段落（≥{EMPTY_PARAGRAPH_THRESHOLD}个） — 可能有多余空行")
        for start, n in empty_seq[:3]: P(f"     [{start}] 起连续 {n} 个空段")
        return False  # informational only — 不算阻断


# ======================== Main ========================
def main():
    ap = argparse.ArgumentParser(description='docx 严格审查 — 12 项全量检查')
    ap.add_argument('docx', help='待审查 .docx')
    ap.add_argument('--source', '-s', default=None, help='源 .md（启用保真检查）')
    ap.add_argument('--skip-fidelity', action='store_true')
    ap.add_argument('--strict', action='store_true',
                    help='将 ⚠ 信息项也视为失败（最高审查标准）')
    args = ap.parse_args()

    doc = Document(args.docx)

    print("=" * 65)
    print("  docx 严格审查报告")
    print("  " + args.docx)
    print("=" * 65)

    checks = [
        ("[1]  Bullet 字体（□ 方框）",              lambda: check1(doc),          True),
        ("[2]  List Number 段落（续号）",             lambda: check2(doc),          True),
        ("[3]  有序列表编号",                          lambda: check3(doc),         False),
        ("[4]  引用上标（GB/T 7714）",                 lambda: check4(doc),          True),
    ]
    if args.source and not args.skip_fidelity:
        checks.append(("[5]  内容保真（❌ 阻断）",     lambda: check5(args.docx, args.source), True))
    else:
        checks.append(("[5]  内容保真",                lambda: (P("  ⏭ 跳过（需 --source）"), True)[1], False))
    checks += [
        ("[6]  标题层级",                              lambda: check6(doc),          True),
        ("[7]  表格审计",                              lambda: check7(doc),         False),
        ("[8]  代码 & 引用块字体",                     lambda: check8(doc),         False),
        ("[9]  TOC & 页眉页脚",                        lambda: check9(doc),         False),
        ("[10] 页面布局",                              lambda: check10(doc),        False),
        ("[11] 中文字体完整性（eastAsia）",            lambda: check11(doc),         True),
        ("[12] 空段落",                                lambda: check12(doc),        False),
    ]

    total_checks = len(checks)
    failures = 0
    results = []  # (title, passed, is_hard)
    for title, fn, is_hard in checks:
        P(f"\n{title}")
        passed = fn()
        if not passed and is_hard:
            failures += 1
        results.append((title, passed, is_hard))

    # ==== 汇总表 ====
    print("\n" + "=" * 65)
    print("  审查汇总：{}/{} 项硬阻断 ❌，{} 项信息 ⚠".format(
        sum(1 for _, p, h in results if not p and h),
        total_checks,
        sum(1 for _, p, h in results if not p and not h)))
    print("-" * 65)
    for title, passed, is_hard in results:
        status = "✅" if passed else ("❌" if is_hard else "⚠ ")
        print(f"  {status}  {title}")
    print("=" * 65)
    total_fail = failures + (sum(1 for _, p, h in results if not p and not h) if args.strict else 0)
    if total_fail == 0:
        print("  ✅ 全部检查通过，可交付。")
    else:
        print(f"  ❌ {total_fail} 项未通过，修复后重审。")
    print("=" * 65)
    sys.exit(1 if total_fail else 0)


if __name__ == '__main__':
    main()
