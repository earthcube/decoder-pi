#!/usr/bin/env python3
"""Earthsurface catalog inventory: providers, themes, formats, AI-metadata flag."""

from __future__ import annotations

import argparse
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


def classify_theme(name: str | None, kw: str | None) -> str:
    blob = f"{name or ''} {kw or ''}".lower()
    if "chelsa" in blob or "terraclimate" in blob:
        return "climate"
    if "hydrograph" in blob or "{tile" in blob:
        return "hydrography"
    if any(x in blob for x in ("land cover", "land_cover", "nlcd", "nalcms")):
        return "land cover"
    if "gpp" in blob or "mod17" in blob or "photosynthesis" in blob:
        return "GPP"
    if any(x in blob for x in ("litholog", "glhymps", "glorich", "geochem", "permeability")):
        return "geochemistry"
    if "soil" in blob:
        return "soil"
    if "grace" in blob or "irrigation" in blob or "streamflow" in blob:
        return "water"
    return "other"


def cmd_providers(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "providers.rq",
        timeout=args.timeout,
    )
    rows = require_rows(data, "providers")
    counts: Counter[str] = Counter()
    for row in rows:
        name = row.get("provider")
        n = row.get("n") or row.get("count") or "0"
        if name:
            try:
                counts[str(name)] += int(float(n))
            except ValueError:
                counts[str(name)] += 1
    if not counts:
        print("No provider counts.")
        return
    _barh(counts, "datasets", args.title or "Earthsurface datasets per provider", _out_path(args, "surface-providers"))


def cmd_themes(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "datasets.rq",
        limit=args.limit or 2000,
        timeout=args.timeout,
    )
    rows = require_rows(data, "datasets")
    by_id: dict[str, str] = {}
    for row in rows:
        did = str(row.get("d") or "")
        if not did or did in by_id:
            continue
        by_id[did] = classify_theme(row.get("name"), row.get("kw"))
    counts = Counter(by_id.values())
    _barh(counts, "datasets", args.title or "Earthsurface themes (from name/keywords)", _out_path(args, "surface-themes"))


def cmd_formats(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "formats.rq",
        limit=args.limit or 40,
        timeout=args.timeout,
    )
    rows = require_rows(data, "formats")
    counts: Counter[str] = Counter()
    for row in rows:
        fmt = str(row.get("fmt") or "").strip("[]").strip()
        n = row.get("n") or "0"
        if not fmt:
            continue
        try:
            counts[fmt] += int(float(n))
        except ValueError:
            counts[fmt] += 1
    _barh(counts, "downloads", args.title or "DataDownload encodingFormat", _out_path(args, "surface-formats"))


def cmd_ai_flag(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "datasets.rq",
        limit=args.limit or 2000,
        timeout=args.timeout,
    )
    rows = require_rows(data, "datasets")
    flagged = []
    seen = set()
    for row in rows:
        kw = str(row.get("kw") or "")
        if "ai-generated" not in kw.lower():
            continue
        did = str(row.get("d") or "")
        if did in seen:
            continue
        seen.add(did)
        flagged.append((row.get("name") or did, kw))
    print(f"AI-generated metadata datasets: {len(flagged)}")
    print("| name | keyword |")
    print("| --- | --- |")
    for name, kw in flagged[:40]:
        print(f"| {name} | {kw} |")
    if args.output:
        print(f"(ai-flag writes no PNG; ignoring {args.output})")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Earthsurface catalog inventory")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, help_, lim in (
        ("providers", cmd_providers, "Datasets per Gleaner provider", None),
        ("themes", cmd_themes, "Theme bars from names/keywords", 2000),
        ("formats", cmd_formats, "encodingFormat bars", 40),
        ("ai-flag", cmd_ai_flag, "List datasets tagged AI-generated metadata", 2000),
    ):
        p = sub.add_parser(name, help=help_)
        _add_io(p, lim)
        p.set_defaults(func=func)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
