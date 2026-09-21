#!/usr/bin/env python3
"""Catalog plots from SPARQL JSON: bars, depth histogram, min/max ranges."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SHARED = Path(__file__).resolve().parents[2] / "_shared"
sys.path.insert(0, str(SHARED))
from cli import (  # noqa: E402
    default_png,
    localname,
    require_rows,
    resolve_result,
    to_float,
)

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUERIES = SKILL_ROOT / "queries"
BIN_ORDER = ["<50", "50-200", "200-1000", "1000-4000", ">=4000"]
MAX_RANGE_ROWS = 80


def _add_io(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--endpoint", help="SPARQL endpoint URL")
    parser.add_argument("--from-json", type=Path, dest="from_json", help="sparql_query.py JSON")
    parser.add_argument("-o", "--output", type=Path, help="PNG path (default: runs/<mode>-<utc>.png)")
    parser.add_argument("--limit", type=int, default=None, help="SPARQL LIMIT when fetching")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--title", default=None, help="Override plot title")


def _out_path(args: argparse.Namespace, mode: str) -> Path:
    path = args.output or default_png(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _savefig(path: Path, title: str) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"Wrote {path}")
    print(f"title: {title}")


def _barh(labels: list[str], values: list[float], xlabel: str, title: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.28 * len(labels) + 1.2)))
    y = range(len(labels) - 1, -1, -1)
    ax.barh(list(y), values, color="#3d6ea8")
    ax.set_yticks(list(y), labels)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    _savefig(out, title)


def cmd_types(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_id="list_types",
        limit=args.limit or 25,
        timeout=args.timeout,
    )
    rows = require_rows(data, "types")
    labels, values = [], []
    for row in rows:
        n = to_float(row.get("count") or row.get("n"))
        if n is None:
            continue
        labels.append(localname(row.get("type")))
        values.append(n)
    if not labels:
        print("No numeric type counts. Nothing plotted.")
        return
    title = args.title or "RDF types (named graphs)"
    _barh(labels, values, "distinct subjects", title, _out_path(args, "types"))
    print(f"rows: {len(labels)}")


def cmd_providers(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "datasets_per_provider.rq",
        timeout=args.timeout,
    )
    rows = require_rows(data, "providers")
    labels, values = [], []
    for row in rows:
        n = to_float(row.get("n") or row.get("count"))
        name = row.get("provider")
        if n is None or not name:
            continue
        labels.append(str(name))
        values.append(n)
    if not labels:
        print("No provider counts. Nothing plotted.")
        return
    title = args.title or "Datasets per provider slug"
    _barh(labels, values, "distinct datasets", title, _out_path(args, "providers"))
    print(f"rows: {len(labels)}")


def cmd_variables(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "top_variables.rq",
        limit=args.limit or 20,
        timeout=args.timeout,
    )
    rows = require_rows(data, "variables")
    labels, values = [], []
    for row in rows:
        n = to_float(row.get("n") or row.get("count"))
        name = row.get("name")
        if n is None or not name:
            continue
        labels.append(str(name))
        values.append(n)
    if not labels:
        print("No variable counts. Nothing plotted.")
        return
    title = args.title or "Top variableMeasured names"
    _barh(labels, values, "distinct datasets", title, _out_path(args, "variables"))
    print(f"rows: {len(labels)}")


def cmd_depth_hist(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "depth_hist.rq",
        timeout=args.timeout,
    )
    rows = require_rows(data, "depth-hist")
    by_bin = {str(r.get("bin")): to_float(r.get("n")) or 0.0 for r in rows if r.get("bin")}
    labels = [b for b in BIN_ORDER if b in by_bin]
    extra = [b for b in by_bin if b not in BIN_ORDER]
    labels.extend(sorted(extra))
    values = [by_bin[b] for b in labels]
    if not labels or sum(values) == 0:
        print("No DepBelowSurf maxValue bins. Nothing plotted.")
        return
    title = args.title or "DepBelowSurf maxValue bins (m)"
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, values, color="#3d6ea8")
    ax.set_xlabel("max depth (m)")
    ax.set_ylabel("distinct datasets")
    ax.set_title(title)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    _savefig(_out_path(args, "depth-hist"), title)
    for lab, val in zip(labels, values):
        print(f"  {lab}: {int(val)}")


def _distinct_ranges(rows: list[dict]) -> list[tuple[str, float, float]]:
    seen: set[tuple[str, float, float]] = set()
    out: list[tuple[str, float, float]] = []
    for row in rows:
        mn = to_float(row.get("minValue"))
        mx = to_float(row.get("maxValue"))
        subj = str(row.get("subj") or "")
        if mn is None or mx is None:
            continue
        key = (subj, mn, mx)
        if key in seen:
            continue
        seen.add(key)
        out.append((localname(subj) or subj, mn, mx))
    return out


def cmd_depth_ranges(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_id="depth_minmax",
        limit=args.limit or 120,
        timeout=args.timeout,
    )
    rows = require_rows(data, "depth-ranges")
    ranges = _distinct_ranges(rows)
    if not ranges:
        print("No numeric DepBelowSurf min/max. Nothing plotted.")
        return
    ranges.sort(key=lambda t: t[2], reverse=True)
    clipped = False
    if len(ranges) > MAX_RANGE_ROWS:
        ranges = ranges[:MAX_RANGE_ROWS]
        clipped = True
    labels = [r[0][:28] for r in ranges]
    mins = [r[1] for r in ranges]
    maxs = [r[2] for r in ranges]
    title = args.title or "DepBelowSurf min–max (m, depth down)"
    fig, ax = plt.subplots(figsize=(9, max(4.0, 0.22 * len(ranges) + 1.4)))
    y = list(range(len(ranges)))
    ax.hlines(y, mins, maxs, color="#3d6ea8", linewidth=2)
    ax.plot(mins, y, "|", color="#1b3f6e")
    ax.plot(maxs, y, "|", color="#1b3f6e")
    ax.set_yticks(y, labels, fontsize=7)
    ax.set_xlabel("depth (m)")
    ax.invert_yaxis()
    ax.set_title(title)
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    _savefig(_out_path(args, "depth-ranges"), title)
    print(f"ranges plotted: {len(ranges)}" + (" (truncated)" if clipped else ""))
    print(f"depth span: {min(mins):.3g} – {max(maxs):.3g} m")


def cmd_summary(args: argparse.Namespace) -> None:
    """Print markdown tables; fetch live queries when --endpoint is set."""
    if args.from_json:
        data = resolve_result(from_json=args.from_json, endpoint=None)
        rows = data.get("rows") or []
        cols = data.get("columns") or (list(rows[0].keys()) if rows else [])
        print(f"rows: {len(rows)}")
        print("| " + " | ".join(cols) + " |")
        print("| " + " | ".join("---" for _ in cols) + " |")
        for row in rows[:25]:
            print("| " + " | ".join(str(row.get(c) or "")[:48] for c in cols) + " |")
        return
    if not args.endpoint:
        print("Error: summary needs --endpoint or --from-json", file=sys.stderr)
        sys.exit(1)
    chunks = [
        ("types", dict(query_id="list_types", limit=10)),
        ("providers", dict(query_file=QUERIES / "datasets_per_provider.rq")),
        ("variables", dict(query_file=QUERIES / "top_variables.rq", limit=10)),
        ("depth-hist", dict(query_file=QUERIES / "depth_hist.rq")),
    ]
    for label, kwargs in chunks:
        print(f"\n## {label}")
        data = resolve_result(from_json=None, endpoint=args.endpoint, timeout=args.timeout, **kwargs)
        rows = data.get("rows") or []
        if not rows:
            print("(empty)")
            continue
        cols = data.get("columns") or list(rows[0].keys())
        print("| " + " | ".join(cols) + " |")
        print("| " + " | ".join("---" for _ in cols) + " |")
        for row in rows[:12]:
            print("| " + " | ".join(str(row.get(c) or "")[:48] for c in cols) + " |")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot catalog analytics from SPARQL JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, help_ in (
        ("types", cmd_types, "Bar chart of rdf:type counts (list_types)"),
        ("providers", cmd_providers, "Bar chart of datasets per provider slug"),
        ("variables", cmd_variables, "Bar chart of top variableMeasured names"),
        ("depth-hist", cmd_depth_hist, "DepBelowSurf maxValue bins"),
        ("depth-ranges", cmd_depth_ranges, "Min–max depth strip"),
        ("summary", cmd_summary, "Markdown tables, no PNG"),
    ):
        p = sub.add_parser(name, help=help_)
        _add_io(p)
        p.set_defaults(func=func)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
