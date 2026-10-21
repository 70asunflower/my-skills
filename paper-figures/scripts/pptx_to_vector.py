# -*- coding: utf-8 -*-
"""Convert an edited paper-figure PPTX into cropped vector PDF + 600dpi PNG
(paper-figures skill).

Pipeline (per requested slide):
  1. PowerPoint COM opens the pptx (ReadOnly), exports ONE vector PDF of the
     whole deck to a temp dir.
  2. Per slide, the union bbox of all shapes is measured live — this adapts
     to whatever the user moved/edited.
  3. PyMuPDF show_pdf_page(clip = bbox + hairline margin) writes a cropped
     vector page (content stays vector; embedded photos stay raster inside).
  4. A 600-dpi PNG is rendered from the cropped PDF.

Usage:
  python pptx_to_vector.py <file.pptx> [--outdir DIR] [--margin 0.05]
                           [--slides 1,2] [--name out_stem]
Requires: pywin32 (PowerPoint installed), pymupdf.
Notes:
  * White margin default 0.05 in (user preference: hairline, not big mats).
  * Output naming: <name or pptx-stem>_slide<k>.pdf/.png unless --name is
    given with a single slide (then plain <name>.pdf/.png).
"""
import os
import sys
import tempfile
import win32com.client
try:
    import pymupdf as fitz   # pymupdf 新名（旧名 fitz 已弃用，将移除）
except ImportError:
    import fitz


def slide_bbox(slide):
    L = T = 1e18
    R = B = -1e18
    for sh in slide.Shapes:
        L = min(L, sh.Left)
        T = min(T, sh.Top)
        R = max(R, sh.Left + sh.Width)
        B = max(B, sh.Top + sh.Height)
    return L, T, R, B


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    ppt = os.path.abspath(args[0])
    outdir = os.path.dirname(ppt)
    margin_in = 0.05
    slides = None
    name = None
    i = 1
    while i < len(args):
        if args[i] == "--outdir":
            outdir = args[i + 1]; i += 2
        elif args[i] == "--margin":
            margin_in = float(args[i + 1]); i += 2
        elif args[i] == "--slides":
            slides = [int(v) for v in args[i + 1].split(",")]; i += 2
        elif args[i] == "--name":
            name = args[i + 1]; i += 2
        else:
            i += 1

    raw_pdf = os.path.join(tempfile.gettempdir(), "pptx_vector_raw.pdf")
    # DispatchEx = separate PowerPoint process: never attaches to an instance
    # the user may be using (their unsaved edits stay safe).
    app = win32com.client.DispatchEx("PowerPoint.Application")
    pres = app.Presentations.Open(ppt, ReadOnly=True, WithWindow=False)
    try:
        n = pres.Slides.Count
        slides = slides or list(range(1, n + 1))
        bboxes = {}
        for k in slides:
            bboxes[k] = slide_bbox(pres.Slides(k))
        pres.SaveAs(raw_pdf, 32)          # 32 = ppSaveAsPDF (vector)
    finally:
        pres.Close()
        if app.Presentations.Count == 0:  # only quit if nothing else is open
            app.Quit()

    src = fitz.open(raw_pdf)
    stem = name or os.path.splitext(os.path.basename(ppt))[0]
    m = margin_in * 72.0                  # in -> pt

    for k in slides:
        L, T, R, B = bboxes[k]
        rect = fitz.Rect(L - m, T - m, R + m, B + m)
        doc = fitz.open()
        page = doc.new_page(width=rect.width, height=rect.height)
        page.show_pdf_page(fitz.Rect(0, 0, rect.width, rect.height), src, k - 1,
                           clip=rect)
        if len(slides) == 1 and name:
            pdf_out = os.path.join(outdir, f"{name}.pdf")
            png_out = os.path.join(outdir, f"{name}.png")
        else:
            pdf_out = os.path.join(outdir, f"{stem}_slide{k}.pdf")
            png_out = os.path.join(outdir, f"{stem}_slide{k}.png")
        doc.save(pdf_out, garbage=4, deflate=True)
        doc.close()
        chk = fitz.open(pdf_out)
        w_in, h_in = chk[0].rect.width / 72, chk[0].rect.height / 72
        chk[0].get_pixmap(dpi=600).save(png_out)
        chk.close()
        print("slide %d -> %.2f x %.2f in  %s | %s" % (k, w_in, h_in, pdf_out, png_out))
    src.close()
    try:
        os.remove(raw_pdf)
    except OSError:
        pass                              # Windows may hold the lock briefly


if __name__ == "__main__":
    main()
