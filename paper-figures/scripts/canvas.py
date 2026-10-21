# -*- coding: utf-8 -*-
"""坐标画布协议 (coordinate canvas) — paper-figures skill.

解决: AI 用代码画图时定位全靠盲猜, 用户反馈"往左/往上/低一点"要靠截图来回猜像素。
约定: 画布先建坐标系, 一切可迭代定位的元素(文本/箭头/图元)注册进 Canvas; 出图附带
*_grid.png(叠加分数网格, 无裁边) 与 *_layout.txt(元素坐标表 + 程序化碰撞报告);
用户照网格直接报坐标或点名元素, AI 改坐标重跑, 不再走截图定位。

坐标语言:
  fig  = 画布分数坐标 (0-1, 原点左下) —— 主语言, 与 *_grid.png 刻度一致
  mm   = 距左下角物理毫米 —— 换算辅助 (画布物理尺寸固定后 1:1)
  data = 数据坐标 —— 仅用于需要随轴联动的元素
  pptx = cm, 原点左上, y 向下 (PPT 惯例, 见 dump_pptx_layout)

用法(matplotlib 管线):
    import sys; sys.path.insert(0, r"C:/Users/qilin/.zcode/skills/paper-figures/scripts")
    from canvas import Canvas
    fig = plt.figure(figsize=(3.4, 3.2)); ax = fig.add_subplot(111)
    c = Canvas(fig, default_ax=ax)
    c.text("t_beam", 0.42, 0.35, "48 MeV", coord="fig", fontsize=8)
    c.arrow("ar1", (0.30, 0.50), (0.20, 0.60), coord="fig",
            arrowprops=dict(arrowstyle="->", lw=0.6))
    c.save("out/fig2_xxx")   # -> .pdf/.png + _grid.png + _layout.txt
注意: 经 Canvas 放置的元素不要再传 transform/xycoords。

命令行(给任意 PNG 烧网格, 用户照图报坐标; 复杂版式可先出空白画布对分区):
    python canvas.py grid 参考.png 参考_grid.png --width-in 3.4 --height-in 3.2
    python canvas.py preview 空白画布.png --width-in 3.4 --height-in 3.2
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GRID_C = "#1F6FD6"


class Canvas:
    """画布分数(0-1)+mm 双语言坐标系, 管一切可迭代定位的元素。"""

    def __init__(self, fig, default_ax=None):
        self.fig = fig
        self.default_ax = default_ax
        self.items = {}  # name -> {kind, artist, coord, xy}

    # ---------- 坐标换算 ----------
    @property
    def size_in(self):
        return tuple(float(v) for v in self.fig.get_size_inches())

    @property
    def size_mm(self):
        return tuple(v * 25.4 for v in self.size_in)

    def to_fig(self, x, y, coord="fig", ax=None):
        """任意语言 -> 画布分数坐标。"""
        if coord == "fig":
            return float(x), float(y)
        if coord == "mm":
            W, H = self.size_mm
            return float(x) / W, float(y) / H
        if coord == "data":
            ax = ax or self.default_ax
            if ax is None:
                raise ValueError("coord='data' 需要 ax 或 default_ax")
            dx, dy = ax.transData.transform((float(x), float(y)))
            fx, fy = self.fig.transFigure.inverted().transform((dx, dy))
            return float(fx), float(fy)
        raise ValueError(f"未知坐标语言 {coord!r}(可用 fig/mm/data)")

    def to_mm(self, fx, fy):
        W, H = self.size_mm
        return fx * W, fy * H

    # ---------- 元素注册 ----------
    def _register(self, name, kind, artist, coord, xy):
        if name in self.items:
            raise ValueError(f"元素重名: {name}")
        self.items[name] = {"kind": kind, "artist": artist, "coord": coord, "xy": xy}

    def text(self, name, x, y, s, coord="fig", ax=None, **kw):
        """注册并放置文本。coord='data' 放进 ax; fig/mm 放画布级 fig.text。"""
        ax = ax or self.default_ax
        fx, fy = self.to_fig(x, y, coord, ax)
        if coord == "data":
            artist = ax.text(x, y, s, **kw)
        else:
            artist = self.fig.text(fx, fy, s, **kw)
        self._register(name, "text", artist, coord, (fx, fy))
        return artist

    def arrow(self, name, xy, xytext, s="", coord="fig", ax=None, arrowprops=None, **kw):
        """注册并放置带箭头标注; xy=箭头尖端, xytext=文本落点。"""
        ax = ax or self.default_ax
        if ax is None:
            raise ValueError("arrow 需要 ax 或 default_ax")
        if coord == "fig":
            rec = ((float(xy[0]), float(xy[1])), (float(xytext[0]), float(xytext[1])))
            artist = ax.annotate(s, xy=xy, xytext=xytext, xycoords="figure fraction",
                                 textcoords="figure fraction",
                                 arrowprops=arrowprops, **kw)
        elif coord == "mm":
            f1, f2 = self.to_fig(xy[0], xy[1], "mm"), self.to_fig(xytext[0], xytext[1], "mm")
            rec = (f1, f2)
            artist = ax.annotate(s, xy=f1, xytext=f2, xycoords="figure fraction",
                                 textcoords="figure fraction",
                                 arrowprops=arrowprops, **kw)
        elif coord == "data":
            artist = ax.annotate(s, xy=xy, xytext=xytext, arrowprops=arrowprops, **kw)
            rec = (self.to_fig(xy[0], xy[1], "data", ax),
                   self.to_fig(xytext[0], xytext[1], "data", ax))
        else:
            raise ValueError(f"未知坐标语言 {coord!r}")
        self._register(name, "arrow", artist, coord, rec)
        return artist

    def register(self, name, artist, coord="fig", xy=None):
        """注册任意已有 artist(补丁/线/图例等), 供 layout 表与碰撞检查。"""
        self._register(name, "artist", artist, coord, xy)

    # ---------- 测量与碰撞 ----------
    def _renderer(self):
        self.fig.canvas.draw()
        try:
            return self.fig.canvas.get_renderer()
        except AttributeError:  # 非 Agg 后端兜底
            return self.fig.canvas.renderer

    def _measure(self):
        rend = self._renderer()
        inv = self.fig.transFigure.inverted()
        rows = []
        for name, it in self.items.items():
            dbbox = None
            try:
                dbbox = it["artist"].get_window_extent(renderer=rend)
            except Exception:  # 3D/特殊 artist 测不了就标 n/a
                pass
            fbbox = None
            if dbbox is not None:
                (fx0, fy0) = inv.transform((dbbox.x0, dbbox.y0))
                (fx1, fy1) = inv.transform((dbbox.x1, dbbox.y1))
                fbbox = (fx0, fy0, fx1, fy1)
            rows.append({"name": name, "kind": it["kind"], "coord": it["coord"],
                         "xy": it["xy"], "dbbox": dbbox, "fbbox": fbbox})
        return rows

    def _overlaps(self, rows, pad_pt=0.7):
        """文本/箭头两两包围盒相交检查, 返回 (a, b, 重叠宽mm, 重叠高mm)。"""
        dpi = float(self.fig.dpi)
        pad = pad_pt / 72.0 * dpi
        out = []
        cand = [r for r in rows if r["dbbox"] is not None and r["kind"] in ("text", "arrow")]
        for i in range(len(cand)):
            for j in range(i + 1, len(cand)):
                bi, bj = cand[i]["dbbox"], cand[j]["dbbox"]
                ox = min(bi.x1 + pad, bj.x1 + pad) - max(bi.x0 - pad, bj.x0 - pad)
                oy = min(bi.y1 + pad, bj.y1 + pad) - max(bi.y0 - pad, bj.y0 - pad)
                if ox > 0 and oy > 0:
                    mmpx = 25.4 / dpi
                    out.append((cand[i]["name"], cand[j]["name"], ox * mmpx, oy * mmpx))
        return out

    # ---------- 网格叠加 ----------
    def grid_overlay(self, step=0.1):
        """在 fig 上叠加全幅分数网格(迭代工件; 定稿前移除)。返回 overlay axes。"""
        W_in, H_in = self.size_in
        W, H = self.size_mm
        g = self.fig.add_axes([0, 0, 1, 1])
        g.set_zorder(1e5)
        g.set_xlim(0, 1)
        g.set_ylim(0, 1)
        g.axis("off")
        g.patch.set_alpha(0.0)
        half = step / 2.0
        n_half = int(round(1.0 / half))
        n = int(round(1.0 / step))

        def is_major(v):
            return abs(v / step - round(v / step)) < 1e-6

        for i in range(1, n_half):
            v = i * half
            if not is_major(v):
                g.plot([v, v], [0, 1], color=GRID_C, lw=0.35, alpha=0.15, zorder=1e5)
                g.plot([0, 1], [v, v], color=GRID_C, lw=0.35, alpha=0.15, zorder=1e5)
        for i in range(1, n):
            v = i * step
            g.plot([v, v], [0, 1], color=GRID_C, lw=0.55, alpha=0.45, zorder=1e5)
            g.plot([0, 1], [v, v], color=GRID_C, lw=0.55, alpha=0.45, zorder=1e5)
        box = dict(facecolor="white", edgecolor="none", alpha=0.8, pad=0.6)
        for i in range(1, n):
            v = i * step
            g.text(v, 0.006, f"{v:.2f}".rstrip("0").rstrip("."), color=GRID_C,
                   fontsize=6, ha="center", va="bottom", zorder=1e6, bbox=box)
            g.text(0.004, v, f"{v:.2f}".rstrip("0").rstrip("."), color=GRID_C,
                   fontsize=6, ha="left", va="center", zorder=1e6, bbox=box)
        note = (f"grid {step:g} = {W * step:.1f} mm | canvas "
                f"{W_in:.2f}x{H_in:.2f} in = {W:.1f}x{H:.1f} mm")
        g.text(0.997, 0.994, note, color=GRID_C, fontsize=6, ha="right", va="top",
               zorder=1e6, bbox=dict(facecolor="white", edgecolor="none",
                                     alpha=0.85, pad=0.8))
        return g

    # ---------- 导出 ----------
    def save(self, base, formats=("pdf", "png"), dpi=600, tight=True, tight_pad=0.02,
             grid=True, grid_step=0.1, layout=True):
        """定稿格式 + 两个迭代工件: *_grid.png(无裁边, 坐标 1:1) + *_layout.txt。

        返回 (rows, overlaps); overlaps 非空时应先自修再交验。
        """
        base = Path(base)
        for ext in formats:
            kw = {"dpi": dpi} if ext == "png" else {}
            if tight:
                kw.update(bbox_inches="tight", pad_inches=tight_pad)
            self.fig.savefig(str(base) + "." + ext, **kw)
        rows = self._measure()
        overlaps = self._overlaps(rows)
        if grid:
            g = self.grid_overlay(grid_step)
            keep = [(a, a.get_position(True)) for a in self.fig.axes if a is not g]
            try:
                # 不用 bbox_inches='tight': 保持像素<->画布分数 1:1, 坐标才有意义
                self.fig.savefig(str(base) + "_grid.png", dpi=dpi)
            finally:
                for a, pos in keep:
                    a.set_position(pos)
                self.fig.delaxes(g)
        if layout:
            self._write_layout(str(base) + "_layout.txt", rows, overlaps)
        return rows, overlaps

    def _write_layout(self, path, rows, overlaps):
        W_in, H_in = self.size_in
        W, H = self.size_mm
        lines = []
        ap = lines.append
        stem = Path(path).name[: -len("_layout.txt")]
        ap(f"# layout manifest — {stem}")
        ap(f"# canvas: {W_in:.2f} x {H_in:.2f} in  ({W:.1f} x {H:.1f} mm)")
        ap("# 坐标语言: fig = 画布分数(0-1, 原点左下, 与 *_grid.png 刻度一致); mm = 距左下角毫米")
        ap("# 反馈: '把 <name> 移到 (fx, fy)' / '在 (fx, fy) 加 ...' — 改脚本坐标重跑, 不用截图")
        ap("")
        ap(f"{'name':<16}{'kind':<8}{'fig_x':>7}{'fig_y':>7}{'mm_x':>8}{'mm_y':>8}   bbox_mm[x0,y0,x1,y1]")
        for r in rows:
            xy = r["xy"]
            if r["fbbox"] is None:
                ap(f"{r['name']:<16}{r['kind']:<8}{'-':>7}{'-':>7}{'-':>8}{'-':>8}   n/a(bbox)")
                continue
            if xy is None:
                fx, fy = (r["fbbox"][0] + r["fbbox"][2]) / 2, (r["fbbox"][1] + r["fbbox"][3]) / 2
            else:
                p = xy[0] if isinstance(xy[0], (tuple, list)) else xy
                fx, fy = p
            mx, my = fx * W, fy * H
            b = r["fbbox"]
            bb = (f"[{b[0] * W:.1f},{b[1] * H:.1f},{b[2] * W:.1f},{b[3] * H:.1f}]")
            ap(f"{r['name']:<16}{r['kind']:<8}{fx:>7.3f}{fy:>7.3f}{mx:>8.1f}{my:>8.1f}   {bb}")
        ap("")
        if overlaps:
            ap("## 碰撞(包围盒重叠, pad 0.7pt) — 先自修再交验")
            for a, b, ox, oy in overlaps:
                ap(f"  {a} <-> {b}: 重叠 {ox:.1f} x {oy:.1f} mm")
        else:
            ap("## 碰撞: 无")
        Path(path).write_text("\n".join(lines), encoding="utf-8")


# ---------- 命令行与独立工具 ----------
def draw_grid_on_png(src, out, width_in=None, height_in=None, dpi=300, step=0.1):
    """给任意 PNG 烧上分数网格(参考图/用户截图取坐标用)。"""
    src, out = Path(src), Path(out)
    img = plt.imread(str(src))
    h_px, w_px = img.shape[0], img.shape[1]
    if width_in is None:
        width_in = w_px / float(dpi)
    if height_in is None:
        height_in = h_px / float(dpi)
    fig = plt.figure(figsize=(width_in, height_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img, extent=[0, 1, 0, 1], aspect="auto", interpolation="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    Canvas(fig).grid_overlay(step)
    fig.savefig(str(out), dpi=dpi)
    plt.close(fig)
    return out


def preview(out, width_in, height_in, step=0.1, dpi=300):
    """空白带坐标画布: 复杂版式先出这张跟人对分区, 再落元素。"""
    fig = plt.figure(figsize=(width_in, height_in))
    Canvas(fig).grid_overlay(step)
    fig.savefig(str(out), dpi=dpi)
    plt.close(fig)
    return Path(out)


def dump_pptx_layout(prs, out_path, title=""):
    """python-pptx 形状清单 -> *_layout.txt (cm, 原点左上, y 向下)。

    建页时给每个形状设语义名 shape.name = "t_beam" 之类, 迭代反馈直接点名。
    """
    lines = []
    ap = lines.append
    sw_cm, sh_cm = prs.slide_width / 360000.0, prs.slide_height / 360000.0
    ap(f"# pptx layout manifest{' — ' + title if title else ''}")
    ap(f"# slide: {sw_cm:.2f} x {sh_cm:.2f} cm (原点左上, y 向下)")
    ap("# 反馈: '把 <name> 移到 (x, y) cm' / '移到画面左上角约 (2, 1)' — 改脚本重跑")
    ap("")
    ap(f"{'slide':>5}  {'name':<22}{'x_cm':>7}{'y_cm':>7}{'w_cm':>7}{'h_cm':>7}")
    for idx, slide in enumerate(prs.slides, 1):
        for sh in slide.shapes:
            try:
                x, y = sh.left / 360000.0, sh.top / 360000.0
                w, h = sh.width / 360000.0, sh.height / 360000.0
            except TypeError:
                x = y = w = h = float("nan")
            ap(f"{idx:>5}  {str(sh.name):<22}{x:>7.2f}{y:>7.2f}{w:>7.2f}{h:>7.2f}")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return Path(out_path)


def main(argv=None):
    p = argparse.ArgumentParser(description="坐标画布协议工具 (paper-figures skill)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("preview", help="空白带坐标网格画布")
    pv.add_argument("out")
    pv.add_argument("--width-in", type=float, required=True)
    pv.add_argument("--height-in", type=float, required=True)
    pv.add_argument("--step", type=float, default=0.1)
    pv.add_argument("--dpi", type=float, default=300)

    gr = sub.add_parser("grid", help="给任意 PNG 烧坐标网格")
    gr.add_argument("src")
    gr.add_argument("out")
    gr.add_argument("--width-in", type=float, default=None,
                    help="物理宽(in); 缺省按 px/--dpi 推算")
    gr.add_argument("--height-in", type=float, default=None)
    gr.add_argument("--dpi", type=float, default=300)
    gr.add_argument("--step", type=float, default=0.1)

    args = p.parse_args(argv)
    if args.cmd == "preview":
        out = preview(args.out, args.width_in, args.height_in, step=args.step, dpi=args.dpi)
    else:
        out = draw_grid_on_png(args.src, args.out, width_in=args.width_in,
                               height_in=args.height_in, dpi=args.dpi, step=args.step)
    print("saved:", out)


if __name__ == "__main__":
    main()
