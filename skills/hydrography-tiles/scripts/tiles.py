#!/usr/bin/env python3
"""Hydrography90m 20° tile index: grid map, lat/lon lookup, GeoTIFF layers."""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

SHARED = Path(__file__).resolve().parents[2] / "_shared"
MAP_SCRIPTS = Path(__file__).resolve().parents[2] / "catalog-map" / "scripts"
sys.path.insert(0, str(SHARED))
sys.path.insert(0, str(MAP_SCRIPTS))
from cli import default_png, require_rows, resolve_result  # noqa: E402
import map as catalog_map  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUERIES = SKILL_ROOT / "queries"
TILE_RE = re.compile(r"\{tile\s+(h\d+v\d+)\}", re.IGNORECASE)
BBOX_RE = re.compile(r"bounding box\s+\(([^)]+)\)", re.IGNORECASE)
FILE_RE = re.compile(r"([A-Za-z0-9_.-]+)\.tif", re.IGNORECASE)


def _add_io(parser: argparse.ArgumentParser, default_limit: int) -> None:
    parser.add_argument("--endpoint", help="SPARQL endpoint URL")
    parser.add_argument("--from-json", type=Path, dest="from_json")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--title", default=None)
    parser.add_argument("--no-coastlines", dest="coastlines", action="store_false")
    parser.set_defaults(coastlines=True)


def _out_path(args: argparse.Namespace, mode: str) -> Path:
    path = args.output or default_png(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def parse_tile_name(name: str | None) -> dict | None:
    """Extract tile id and (west, south, east, north) from a hydrography dataset name."""
    if not name:
        return None
    tm = TILE_RE.search(name)
    bm = BBOX_RE.search(name)
    if not tm or not bm:
        return None
    nums = [float(x) for x in bm.group(1).split() if x]
    if len(nums) != 4:
        return None
    lat1, lon1, lat2, lon2 = nums
    south, north = sorted((lat1, lat2))
    west, east = sorted((lon1, lon2))
    return {
        "tile": tm.group(1).lower(),
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "name": name,
    }


def parse_layer_url(url: str) -> tuple[str | None, str | None]:
    """Return (layer_stem, tile_id) from an IGB GeoTIFF URL."""
    raw = unquote(url or "")
    parsed = urlparse(raw)
    qs = parse_qs(parsed.query)
    files = (qs.get("files") or [""])[0]
    path = qs.get("path") or [""]
    blob = files or Path(parsed.path).name
    fm = FILE_RE.search(blob)
    if not fm:
        return None, None
    stem = fm.group(1)
    tile_m = re.search(r"(h\d+v\d+)$", stem, re.IGNORECASE)
    tile = tile_m.group(1).lower() if tile_m else None
    layer = stem[: tile_m.start() - 1] if tile_m and tile_m.start() > 1 else stem
    if not layer and path:
        layer = Path(path[0]).name
    return layer, tile


def contains(tile: dict, lat: float, lon: float) -> bool:
    return tile["south"] <= lat <= tile["north"] and tile["west"] <= lon <= tile["east"]


def _tiles_from_args(args: argparse.Namespace) -> list[dict]:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "tile_datasets.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    rows = require_rows(data, "hydrography datasets")
    tiles = []
    seen = set()
    for row in rows:
        parsed = parse_tile_name(row.get("name"))
        if not parsed or parsed["tile"] in seen:
            continue
        seen.add(parsed["tile"])
        parsed["d"] = row.get("d")
        tiles.append(parsed)
    return tiles


def cmd_grid(args: argparse.Namespace) -> None:
    tiles = _tiles_from_args(args)
    if not tiles:
        print("No parseable hydrography tile names.")
        return
    title = args.title or f"hydrography90m 20° tiles (n={len(tiles)})"
    _, ax = catalog_map._base_axes(title, coastlines=args.coastlines)
    for t in tiles:
        w = t["east"] - t["west"]
        h = t["north"] - t["south"]
        ax.add_patch(
            Rectangle(
                (t["west"], t["south"]),
                w,
                h,
                fill=False,
                edgecolor="#3d6ea8",
                linewidth=0.6,
                alpha=0.8,
                zorder=2,
            )
        )
        ax.text(
            t["west"] + w / 2,
            t["south"] + h / 2,
            t["tile"],
            ha="center",
            va="center",
            fontsize=5,
            color="#1b3f6e",
            zorder=3,
        )
    out = _out_path(args, "hydro-grid")
    catalog_map._savefig(out, title)
    print(f"tiles: {len(tiles)}")


def cmd_lookup(args: argparse.Namespace) -> None:
    tiles = _tiles_from_args(args)
    hits = [t for t in tiles if contains(t, args.lat, args.lon)]
    print(f"point: {args.lat}, {args.lon}")
    print(f"matching tiles: {len(hits)}")
    print("| tile | west | south | east | north |")
    print("| --- | --- | --- | --- | --- |")
    for t in hits:
        print(f"| {t['tile']} | {t['west']:g} | {t['south']:g} | {t['east']:g} | {t['north']:g} |")
    if not hits:
        print("No tile contains this point (or tile names did not parse).")
        return
    title = args.title or f"tile lookup {args.lat:g},{args.lon:g}"
    _, ax = catalog_map._base_axes(title, coastlines=args.coastlines)
    for t in tiles:
        ax.add_patch(
            Rectangle(
                (t["west"], t["south"]),
                t["east"] - t["west"],
                t["north"] - t["south"],
                fill=False,
                edgecolor="#bbbbbb",
                linewidth=0.4,
                zorder=1,
            )
        )
    for t in hits:
        ax.add_patch(
            Rectangle(
                (t["west"], t["south"]),
                t["east"] - t["west"],
                t["north"] - t["south"],
                fill=False,
                edgecolor="#c23b22",
                linewidth=1.4,
                zorder=2,
            )
        )
        ax.text(
            (t["west"] + t["east"]) / 2,
            (t["south"] + t["north"]) / 2,
            t["tile"],
            ha="center",
            va="center",
            color="#c23b22",
            fontsize=8,
            zorder=3,
        )
    ax.plot(args.lon, args.lat, "+", color="#1b3f6e", markersize=12, zorder=4)
    catalog_map._savefig(_out_path(args, "hydro-lookup"), title)


def cmd_layers(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "tile_downloads.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    rows = require_rows(data, "hydrography downloads")
    want = args.tile.lower() if args.tile else None
    by_layer: dict[str, list[str]] = defaultdict(list)
    n = 0
    for row in rows:
        url = str(row.get("url") or "")
        layer, tile = parse_layer_url(url)
        if not layer:
            parsed = parse_tile_name(row.get("name"))
            tile = parsed["tile"] if parsed else tile
        if want and tile != want:
            # also match filename
            if want not in url.lower() and want not in str(row.get("name") or "").lower():
                continue
        by_layer[layer or "(unknown)"].append(url)
        n += 1
    print(f"urls: {n} tile_filter: {want or '(all)'}")
    print("| layer | n | example |")
    print("| --- | --- | --- |")
    for layer, urls in sorted(by_layer.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"| {layer} | {len(urls)} | {urls[0][:80]} |")
    if args.output:
        print(f"(layers writes no PNG; ignoring {args.output})")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hydrography90m tile index")
    sub = parser.add_subparsers(dest="command", required=True)
    p_grid = sub.add_parser("grid", help="Map 20° tile footprints")
    _add_io(p_grid, 300)
    p_grid.set_defaults(func=cmd_grid)
    p_lu = sub.add_parser("lookup", help="Which tile contains --lat --lon")
    _add_io(p_lu, 300)
    p_lu.add_argument("--lat", type=float, required=True)
    p_lu.add_argument("--lon", type=float, required=True)
    p_lu.set_defaults(func=cmd_lookup)
    p_ly = sub.add_parser("layers", help="GeoTIFF layer stems from contentUrl")
    _add_io(p_ly, 800)
    p_ly.add_argument("--tile", default=None, help="Filter e.g. h10v04")
    p_ly.set_defaults(func=cmd_layers)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
