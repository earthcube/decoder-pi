#!/usr/bin/env python3
"""Ecoforecast catalog inventory: themes, models, column names, site map."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SHARED = Path(__file__).resolve().parents[2] / "_shared"
sys.path.insert(0, str(SHARED))
from cli import default_png, require_rows, resolve_result  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUERIES = SKILL_ROOT / "queries"
MAP_CLI = Path(__file__).resolve().parents[2] / "catalog-map" / "scripts" / "map.py"
STAC_RE = re.compile(
    r"/forecasts/([^/]+)/([^/]+)/models/([^/]+?)(?:\.json)?(?:#.*)?$",
    re.IGNORECASE,
)


def _add_io(parser: argparse.ArgumentParser, default_limit: int | None = 500) -> None:
    parser.add_argument("--endpoint", help="SPARQL endpoint URL")
    parser.add_argument("--from-json", type=Path, dest="from_json")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--title", default=None)


def _out_path(args: argparse.Namespace, mode: str) -> Path:
    path = args.output or default_png(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _barh(counter: Counter[str], xlabel: str, title: str, out: Path) -> None:
    items = counter.most_common()
    labels = [k for k, _ in items]
    values = [float(v) for _, v in items]
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.28 * len(labels) + 1.2)))
    y = range(len(labels) - 1, -1, -1)
    ax.barh(list(y), values, color="#3d6ea8")
    ax.set_yticks(list(y), labels)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"Wrote {out}")
    print(f"title: {title}")
    for lab, val in items:
        print(f"  {lab}: {val}")


def parse_stac(url: str | None, name: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (theme, variable, model) from a neon4cast STAC URL or name."""
    if url:
        match = STAC_RE.search(url)
        if match:
            return match.group(1), match.group(2), match.group(3)
    return None, None, name or None


def _datasets(args: argparse.Namespace) -> list[dict]:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "datasets.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    return require_rows(data, "forecast datasets")


def cmd_themes(args: argparse.Namespace) -> None:
    rows = _datasets(args)
    counts: Counter[str] = Counter()
    unmatched = 0
    for row in rows:
        theme, _var, _model = parse_stac(row.get("url"), row.get("name"))
        if theme:
            counts[theme] += 1
        else:
            unmatched += 1
            counts["(no STAC theme)"] += 1
    if not counts:
        print("No STAC theme paths in dataset URLs. Nothing plotted.")
        print(f"unmatched: {unmatched}")
        return
    title = args.title or "Ecoforecast themes (from STAC URL)"
    _barh(counts, "datasets", title, _out_path(args, "forecast-themes"))
    print(f"unmatched urls: {unmatched}")


def cmd_models(args: argparse.Namespace) -> None:
    rows = _datasets(args)
    counts: Counter[str] = Counter()
    for row in rows:
        _theme, _var, model = parse_stac(row.get("url"), row.get("name"))
        if model:
            counts[model] += 1
    if not counts:
        print("No model names. Nothing plotted.")
        return
    top = Counter(dict(counts.most_common(25)))
    title = args.title or "Ecoforecast model ids (top 25)"
    _barh(top, "datasets", title, _out_path(args, "forecast-models"))
    print(f"distinct models: {len(counts)}")


def cmd_columns(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "variable_names.rq",
        limit=args.limit or 40,
        timeout=args.timeout,
    )
    rows = require_rows(data, "variable names")
    print("These names are forecast-file columns in RDF, not numeric series.")
    print("| name | n |")
    print("| --- | --- |")
    for row in rows:
        print(f"| {row.get('name') or ''} | {row.get('n') or ''} |")
    if args.output:
        print(f"(columns mode writes no PNG; ignoring {args.output})")


def cmd_sites_map(args: argparse.Namespace) -> None:
    """Delegate to catalog-map points (same lat/lon query)."""
    import subprocess

    from cli import REPO_ROOT

    if not MAP_CLI.is_file():
        print(f"Error: catalog-map CLI missing: {MAP_CLI}", file=sys.stderr)
        sys.exit(1)
    out = _out_path(args, "forecast-sites")
    cmd = ["uv", "run", "python", str(MAP_CLI), "points", "-o", str(out), "--timeout", str(args.timeout)]
    if args.from_json:
        cmd += ["--from-json", str(args.from_json)]
    elif args.endpoint:
        cmd += ["--endpoint", args.endpoint, "--limit", str(args.limit or 4000)]
    else:
        print("Error: sites-map needs --from-json or --endpoint", file=sys.stderr)
        sys.exit(1)
    if args.title:
        cmd += ["--title", args.title]
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    sys.exit(proc.returncode)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ecoforecast catalog inventory (not parquet/time-series plots)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_th = sub.add_parser("themes", help="Bar chart of STAC themes")
    _add_io(p_th)
    p_th.set_defaults(func=cmd_themes)
    p_mo = sub.add_parser("models", help="Bar chart of model ids")
    _add_io(p_mo)
    p_mo.set_defaults(func=cmd_models)
    p_co = sub.add_parser("columns", help="Table of variableMeasured names")
    _add_io(p_co, 40)
    p_co.set_defaults(func=cmd_columns)
    p_sm = sub.add_parser("sites-map", help="Lat/lon map via catalog-map")
    _add_io(p_sm, 4000)
    p_sm.set_defaults(func=cmd_sites_map)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
