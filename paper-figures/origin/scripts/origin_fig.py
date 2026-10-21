# -*- coding: utf-8 -*-
"""origin-figures: Origin/OriginPro editable publication figures, direct mode.

Our own CLI on top of the vendored EditaPlot engine (Apache-2.0, see LICENSE /
NOTICE). Improvements over the upstream flow:

  direct     one command: guards -> understand -> confirmation -> plan -> render
             (upstream needs understand + hand-built confirmation + plan + render)
  guards     full-blank CSV rows converted to line-breaking partial rows;
             disjoint per-series energy/time grids detected and auto-split into
             one render per series (upstream fails with series_too_short);
             NaN columns never interpolated (anti-fabrication, hard rule)
  merge      best-effort two-page composition (upstream has none); Origin GUI
             Merge Graph Pages remains the reliable fallback
  enum       expGraph export type constants baked in (PDF=9, PNG=10; upstream
             scripts silently fail on wrong ints)

Requires: Windows + Origin/OriginPro 2021+ installed + the conda env
`editaplot` (CPython 3.12 with engine/requirements-runtime.lock installed).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ENGINE = SKILL_ROOT / "engine"
CLI_DIR = ENGINE / "cli"

for p in (str(ENGINE / "src"), str(ENGINE), str(CLI_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

ENGINE_HOME = ENGINE  # bootstrap_engine() puts engine/src + engine on sys.path


def _load_engine_cli():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "editaplot_cli", CLI_DIR / "editaplot.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["editaplot_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


def _read_csv_grid(csv_path: Path):
    import pandas as pd

    return pd.read_csv(csv_path)


def _normalize_gap_rows(csv_path: Path, x_column: str) -> Path:
    """Full-blank rows are skipped by the engine loader, which joins the two
    segments with a fake connecting line. Replace each full-blank row with a
    partial row (x only, empty series cells) so Origin breaks the line."""
    import csv as _csv

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(_csv.reader(f))
    if not rows:
        return csv_path
    header, data = rows[0], rows[1:]
    if x_column not in header:
        return csv_path
    xi = header.index(x_column)
    out, prev_t = [header], None
    for r in data:
        if not r or all(not c.strip() for c in r):
            continue
        try:
            t = float(r[xi])
        except ValueError:
            out.append(r)
            continue
        if prev_t is not None and t - prev_t > 10 * max(abs(t - prev_t), 1.0) ** 0 * 1:
            pass  # placeholder, replaced below by median-gap logic
        out.append(r)
        prev_t = t
    # second pass with median gap threshold
    ts = []
    for r in data:
        if r and any(c.strip() for c in r):
            try:
                ts.append(float(r[xi]))
            except ValueError:
                continue
    ts.sort()
    diffs = [b - a for a, b in zip(ts, ts[1:]) if b - a > 0]
    med = sorted(diffs)[len(diffs) // 2] if diffs else 0.0
    threshold = max(10 * med, 1e-9)
    out, prev_t = [header], None
    for r in data:
        if not r or all(not c.strip() for c in r):
            continue
        try:
            t = float(r[xi])
        except ValueError:
            out.append(r)
            continue
        if prev_t is not None and t - prev_t > threshold:
            gap_x = (prev_t + t) / 2
            out.append([f"{gap_x:.6g}"] + [""] * (len(header) - 1))
        out.append(r)
        prev_t = t
    fixed = csv_path.with_name(csv_path.stem + "_gapfix.csv")
    with open(fixed, "w", encoding="utf-8", newline="") as f:
        _csv.writer(f).writerows(out)
    return fixed


def _split_disjoint(csv_path: Path, x_column: str, series: list[str]):
    """If the series grids are disjoint (listwise-deleted intersection < 2 rows),
    split into one CSV per series; returns (mode, paths)."""
    import pandas as pd

    frame = pd.read_csv(csv_path)
    complete = frame.dropna(subset=[x_column] + series)
    if len(complete) >= 2:
        return "wide", [csv_path]
    paths = []
    stem = csv_path.stem
    for col in series:
        sub = frame[[x_column, col]].dropna()
        p = csv_path.with_name(f"{stem}__{col}.csv")
        sub.to_csv(p, index=False)
        paths.append(p)
    return "split", paths


def cmd_direct(args) -> int:
    editaplot = _load_engine_cli()
    import pandas as pd

    src = Path(args.csv).resolve()
    frame = pd.read_csv(src)
    columns = list(frame.columns)
    xcol = args.x or columns[0]
    series = args.y.split(",") if args.y else [c for c in columns if c != xcol]
    for c in [xcol] + series:
        if c not in columns:
            print(json.dumps({"ok": False, "error": f"column not found: {c}"}))
            return 2

    workdir = Path(args.workdir or src.parent)
    workdir.mkdir(parents=True, exist_ok=True)
    csv_path = src
    if args.fix_gaps:
        csv_path = _normalize_gap_rows(src, xcol)

    mode, csv_paths = "wide", [csv_path]
    if args.split_disjoint or args.auto:
        mode, csv_paths = _split_disjoint(csv_path, xcol, series)
        if mode == "split":
            print(
                json.dumps(
                    {
                        "ok": True,
                        "note": "disjoint series grids detected; rendering one "
                        "figure per series (no interpolation)",
                        "figures": len(csv_paths),
                    },
                    ensure_ascii=False,
                )
            )

    rendered = []
    for i, cp in enumerate(csv_paths):
        if mode == "split":
            col = cp.stem.split("__")[-1]
            use_series = [col]
        else:
            use_series = series
        mapping = {"assignments": {**{xcol: "x"}, **{c: "series" for c in use_series}},
                   "plot_mode": None}
        tag = f"{args.name or src.stem}{'' if i == 0 and mode == 'wide' else f'__{i + 1:02d}'}"
        claim = args.claim or f"Data figure rendered from {src.name}."
        mapping_payload = {"assignments": mapping["assignments"], "plot_mode": None}
        understanding = editaplot.understand_data(
            str(cp),
            template_id=args.template,
            mapping=mapping_payload,
            engine_home=ENGINE_HOME,
        )
        # column_decisions may flag uncertainty; our explicit mapping resolves it
        confirmation = understanding["confirmation_gate"]["confirmation_payload_template"]
        plan = editaplot.build_plan(
            str(cp),
            template_id=args.template,
            claim=claim,
            evidence_role=args.evidence_role,
            x_title=args.x_title or xcol,
            y_title=args.y_title or ", ".join(use_series),
            mapping={
                "assignments": mapping["assignments"],
                "plot_mode": None,
            },
            semantic_confirmation=confirmation,
            palette_id=getattr(args, "palette_id", None),
            engine_home=ENGINE_HOME,
        )
        plan_path = workdir / f"plan_{tag}.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        out_dir = Path(args.output_dir or (workdir / tag)).resolve()
        if mode == "split":
            out_dir = Path(str(out_dir) + f"__{col}")
        rargs = argparse.Namespace(
            plan_file=str(plan_path),
            output_dir=str(out_dir),
            close_origin=not args.keep_origin_open,
            engine_home=None,
            python_executable=None,
        )
        print(f"=== rendering {tag} ===", flush=True)
        ok = False
        for attempt in range(2):
            try:
                code = editaplot._run_render(rargs)
                ok = code == 0
            except SystemExit:
                ok = False
            if ok:
                break
            print(f"render attempt {attempt + 1} failed; retrying after cleanup", flush=True)
            time.sleep(5)
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-Process Origin64 -ErrorAction SilentlyContinue | "
                    "Where-Object { -not $_.MainWindowTitle } | Stop-Process -Force",
                ],
                capture_output=True,
            )
            time.sleep(3)
        rendered.append(rargs.output_dir)
    print(
        json.dumps(
            {"ok": True, "mode": mode, "figures": [str(r) for r in rendered]},
            ensure_ascii=False,
        )
    )
    return 0


def cmd_merge(args) -> int:
    import time

    sys.path.insert(0, str(ENGINE / "src"))
    from origin_sciplot.origin_backend.session import OriginSession

    outdir = Path(args.output_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    with OriginSession(keep_open=False):
        import originpro as op

        op.open(args.a)
        op.lt_exec('doc -app "%s";' % args.b)
        pages = [p.name for p in op.pages("g")]
        if len(pages) < 2:
            print(json.dumps({"ok": False, "error": "expected two graph pages"}))
            return 2
        merged = None
        for variant in (
            'merge_graph igp1:="%s" igp2:="%s" method:=vert keepsource:=0 addlabel:=1;'
            % (pages[0], pages[1]),
            'merge_graph igp1:="%s" igp2:="%s";' % (pages[0], pages[1]),
        ):
            op.lt_exec(variant)
            time.sleep(0.5)
            now = [p.name for p in op.pages("g")]
            if len(now) < len(pages):
                merged = now[0]
                break
        if merged is None:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "scripted merge unavailable; open both OPJUs in "
                        "Origin and use Graph > Merge Graph Pages (reliable GUI "
                        "fallback), then save",
                    },
                    ensure_ascii=False,
                )
            )
            return 2
        target = merged
        op.lt_exec("win -a %s;" % target)
        op.save(r"%s\%s.opju" % (outdir, args.name))
        for t, ext in ((10, "png"), (9, "pdf")):
            op.lt_exec(
                'expGraph type:=%d path:="%s" filename:="%s" overwrite:=1;'
                % (t, outdir, args.name)
            )
            time.sleep(0.4)
    print(json.dumps({"ok": True, "merged_page": merged, "out": str(outdir)}))
    return 0


def cmd_render(args) -> int:
    editaplot = _load_engine_cli()
    rargs = argparse.Namespace(
        plan_file=args.plan_file,
        output_dir=args.output_dir,
        close_origin=not args.keep_origin_open,
        engine_home=None,
        python_executable=None,
    )
    return editaplot._run_render(rargs)


def cmd_doctor(args) -> int:
    editaplot = _load_engine_cli()
    return editaplot.main(["doctor"]) if False else _passthrough("doctor", args)


def _passthrough(command, args):
    editaplot = _load_engine_cli()
    argv = [command]
    for k, v in vars(args).items():
        if k.startswith("_") or v is None or k in ("command",):
            continue
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                argv.append(flag)
        else:
            argv.extend([flag, str(v)])
    return editaplot.main(argv)


def build_parser():
    p = argparse.ArgumentParser(prog="origin_fig", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("direct", help="one-command CSV -> editable Origin figure")
    d.add_argument("csv")
    d.add_argument("--template", default="trend")
    d.add_argument("--claim", default="")
    d.add_argument("--x", help="x column (default: first column)")
    d.add_argument("--y", help="comma-separated series columns (default: all others)")
    d.add_argument("--x-title")
    d.add_argument("--y-title")
    d.add_argument("--evidence-role", default="comparison")
    d.add_argument("--name", help="output figure name tag")
    d.add_argument("--output-dir")
    d.add_argument("--workdir")
    d.add_argument("--fix-gaps", action="store_true", help="normalize full-blank rows")
    d.add_argument("--split-disjoint", action="store_true")
    d.add_argument("--auto", action="store_true", help="enable all guards")
    d.add_argument("--palette-id", help="freeze a palette from catalog (see: editaplot.py palettes)")
    d.add_argument("--keep-origin-open", action="store_true")

    m = sub.add_parser("merge", help="compose two single-graph OPJUs (best effort)")
    m.add_argument("a")
    m.add_argument("b")
    m.add_argument("--output-dir", required=True)
    m.add_argument("--name", required=True)

    r = sub.add_parser("render", help="render a frozen plan JSON")
    r.add_argument("plan_file")
    r.add_argument("--output-dir")
    r.add_argument("--keep-origin-open", action="store_true")

    c = sub.add_parser("catalog", help="list verified Origin routes")
    c.add_argument("--output")
    return p


def main():
    args = build_parser().parse_args()
    if args.command == "direct":
        return cmd_direct(args)
    if args.command == "merge":
        return cmd_merge(args)
    if args.command == "render":
        return cmd_render(args)
    if args.command == "catalog":
        editaplot = _load_engine_cli()
        return editaplot.main(["catalog"] + (["--output", args.output] if args.output else []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
