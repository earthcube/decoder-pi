#!/usr/bin/env python3
"""List GeoTIFF/GPKG DataDownload URLs from SPARQL. No raster download in v1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

SHARED = Path(__file__).resolve().parents[2] / "_shared"
sys.path.insert(0, str(SHARED))
from cli import require_rows, resolve_result  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUERIES = SKILL_ROOT / "queries"
UA = "decoder-pi-geotiff-list/1.0"


def filename_of(url: str) -> str:
    raw = unquote(url or "")
    parsed = urlparse(raw)
    from urllib.parse import parse_qs

    files = (parse_qs(parsed.query).get("files") or [""])[0]
    if files:
        return files
    return Path(parsed.path).name or raw[-60:]


def cmd_list(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "downloads.rq",
        limit=args.limit or 40,
        timeout=args.timeout,
    )
    rows = require_rows(data, "raster downloads")
    needle = (args.contains or "").lower()
    shown = 0
    print("| file | format | url |")
    print("| --- | --- | --- |")
    for row in rows:
        url = str(row.get("url") or "")
        if needle and needle not in url.lower() and needle not in str(row.get("name") or "").lower():
            continue
        fmt = str(row.get("fmt") or "").strip("[]")
        print(f"| {filename_of(url)} | {fmt} | {url} |")
        shown += 1
        if args.head:
            try:
                req = Request(url, method="HEAD", headers={"User-Agent": UA})
                with urlopen(req, timeout=min(args.timeout, 15)) as resp:
                    length = resp.headers.get("Content-Length") or "?"
                    print(f"  HEAD {resp.status} Content-Length={length}")
            except Exception as exc:
                print(f"  HEAD failed: {exc}")
    print(f"rows shown: {shown} (of {len(rows)})")
    print("v1 lists URLs only; it does not download 90 m GeoTIFF tiles.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List GeoTIFF/GPKG downloads from SPARQL")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list", help="Print download table")
    p.add_argument("--endpoint")
    p.add_argument("--from-json", type=Path, dest="from_json")
    p.add_argument("--contains", default=None)
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--head", action="store_true", help="HTTP HEAD each listed URL for size")
    p.set_defaults(func=cmd_list)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
