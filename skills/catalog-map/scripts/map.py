#!/usr/bin/env python3
"""Maps from SPARQL JSON: lat/lon points, schema:box, GeoSPARQL WKT, haversine near."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

SHARED = Path(__file__).resolve().parents[2] / "_shared"
sys.path.insert(0, str(SHARED))
from cli import default_png, require_rows, resolve_result, to_float  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUERIES = SKILL_ROOT / "queries"
COAST_PATH = SKILL_ROOT / "assets" / "ne_110m_coastline.geojson"
PAIR_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)")
MAX_POINTS = 8000
MAX_BOXES = 400
MAX_WKT_GEOMS = 200
MAX_COORDS_PER_WKT = 4000
EARTH_KM = 6371.0088


def _add_io(parser: argparse.ArgumentParser, default_limit: int) -> None:
    parser.add_argument("--endpoint", help="SPARQL endpoint URL")
    parser.add_argument("--from-json", type=Path, dest="from_json")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--title", default=None)
    parser.add_argument(
        "--coastlines",
        dest="coastlines",
        action="store_true",
        default=True,
        help="Draw bundled 110m coastlines (default)",
    )
    parser.add_argument(
        "--no-coastlines",
        dest="coastlines",
        action="store_false",
        help="Skip coastlines",
    )


def _out_path(args: argparse.Namespace, mode: str) -> Path:
    path = args.output or default_png(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_coastlines() -> list[list[tuple[float, float]]]:
    """Load lon/lat polylines from the bundled Natural Earth 110m coastline."""
    if not COAST_PATH.is_file():
        return []
    data = json.loads(COAST_PATH.read_text(encoding="utf-8"))
    lines: list[list[tuple[float, float]]] = []
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        gtype = geom.get("type")
        if gtype == "LineString":
            lines.append([(float(x), float(y)) for x, y in coords])
        elif gtype == "MultiLineString":
            for part in coords:
                lines.append([(float(x), float(y)) for x, y in part])
    return lines


def draw_coastlines(ax) -> None:
    for line in load_coastlines():
        if len(line) < 2:
            continue
        xs = [p[0] for p in line]
        ys = [p[1] for p in line]
        ax.plot(xs, ys, color="#8a8a8a", linewidth=0.45, zorder=0, solid_capstyle="round")


def _base_axes(title: str, *, coastlines: bool, xlim=None, ylim=None):
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(*(xlim or (-180, 180)))
    ax.set_ylim(*(ylim or (-90, 90)))
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":", alpha=0.35)
    if coastlines:
        draw_coastlines(ax)
    return fig, ax


def _savefig(path: Path, title: str) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"Wrote {path}")
    print(f"title: {title}")


def parse_box(text: str) -> tuple[float, float, float, float] | None:
    """Return (lon0, lat0, width, height) for a matplotlib Rectangle, or None.

    Accepts:
      'minLat minLon maxLat maxLon'  (EMODNet / schema.org box)
      'lat,lon lat,lon'              (neon4cast)
    """
    raw = (text or "").strip()
    if not raw:
        return None
    if "," in raw:
        parts = raw.replace(",", " ").split()
        nums = []
        for p in parts:
            v = to_float(p)
            if v is None:
                return None
            nums.append(v)
        if len(nums) != 4:
            return None
        lat1, lon1, lat2, lon2 = nums
    else:
        parts = raw.split()
        if len(parts) != 4:
            return None
        nums = [to_float(p) for p in parts]
        if any(v is None for v in nums):
            return None
        lat1, lon1, lat2, lon2 = nums  # type: ignore[misc]
    south, north = sorted((lat1, lat2))
    west, east = sorted((lon1, lon2))
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        return None
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return None
    return west, south, east - west, north - south


def parse_wkt_coords(wkt: str) -> list[tuple[float, float]]:
    """Extract (lon, lat) pairs from MULTIPOINT / POLYGON / POINT WKT."""
    coords: list[tuple[float, float]] = []
    for match in PAIR_RE.finditer(wkt or ""):
        lon = to_float(match.group(1))
        lat = to_float(match.group(2))
        if lon is None or lat is None:
            continue
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            coords.append((lon, lat))
        if len(coords) >= MAX_COORDS_PER_WKT:
            break
    return coords


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres (WGS84 mean radius)."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = p2 - p1
    dlon = l2 - l1
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def destination(lat: float, lon: float, bearing_rad: float, km: float) -> tuple[float, float]:
    """Point at distance `km` along `bearing_rad` from (lat, lon)."""
    ang = km / EARTH_KM
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(bearing_rad)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing_rad) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180


def circle_lonlat(lat: float, lon: float, km: float, n: int = 72) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for i in range(n + 1):
        bearing = 2 * math.pi * i / n
        plat, plon = destination(lat, lon, bearing, km)
        xs.append(plon)
        ys.append(plat)
    return xs, ys


def collect_points(rows: list[dict]) -> tuple[list[dict], int]:
    """Return valid point dicts with _lat/_lon and a skipped count."""
    out: list[dict] = []
    skipped = 0
    for row in rows:
        lat = to_float(row.get("lat"))
        lon = to_float(row.get("lon"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            skipped += 1
            continue
        item = dict(row)
        item["_lat"] = lat
        item["_lon"] = lon
        out.append(item)
        if len(out) >= MAX_POINTS:
            break
    return out, skipped


def cmd_points(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "latlon.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    rows = require_rows(data, "points")
    pts, skipped = collect_points(rows)
    if not pts:
        print("No valid lat/lon pairs. Nothing plotted.")
        return
    title = args.title or f"schema:latitude / longitude (n={len(pts)})"
    _, ax = _base_axes(title, coastlines=args.coastlines)
    ax.scatter(
        [p["_lon"] for p in pts],
        [p["_lat"] for p in pts],
        s=8,
        alpha=0.45,
        c="#c23b22",
        linewidths=0,
        zorder=2,
    )
    _savefig(_out_path(args, "points"), title)
    print(f"points: {len(pts)} skipped: {skipped}")


def cmd_boxes(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "boxes.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    rows = require_rows(data, "boxes")
    rects = []
    skipped = 0
    for row in rows:
        parsed = parse_box(str(row.get("box") or ""))
        if parsed is None:
            skipped += 1
            continue
        rects.append(parsed)
        if len(rects) >= MAX_BOXES:
            break
    if not rects:
        print("No parseable schema:box literals. Nothing plotted.")
        return
    title = args.title or f"schema:box footprints (n={len(rects)})"
    _, ax = _base_axes(title, coastlines=args.coastlines)
    for x, y, w, h in rects:
        ax.add_patch(
            Rectangle(
                (x, y),
                w,
                h,
                fill=False,
                edgecolor="#3d6ea8",
                alpha=0.55,
                linewidth=0.8,
                zorder=2,
            )
        )
    _savefig(_out_path(args, "boxes"), title)
    print(f"boxes: {len(rects)} skipped: {skipped}")


def cmd_wkt(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "wkt.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    rows = require_rows(data, "wkt")
    point_x, point_y = [], []
    n_poly = 0
    skipped = 0
    title = args.title or "geo:asWKT"
    _, ax = _base_axes(title, coastlines=args.coastlines)
    for i, row in enumerate(rows):
        if i >= MAX_WKT_GEOMS:
            break
        wkt = str(row.get("wkt") or "")
        coords = parse_wkt_coords(wkt)
        if len(coords) < 1:
            skipped += 1
            continue
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        kind = wkt.strip().upper()
        if kind.startswith("POLYGON") or kind.startswith("MULTIPOLYGON"):
            ax.plot(xs, ys, color="#3d6ea8", linewidth=0.8, alpha=0.7, zorder=2)
            n_poly += 1
        else:
            point_x.extend(xs)
            point_y.extend(ys)
    if point_x:
        ax.scatter(point_x, point_y, s=6, alpha=0.35, c="#c23b22", linewidths=0, zorder=2)
    if not point_x and n_poly == 0:
        print("No parseable WKT coordinates. Nothing plotted.")
        plt.close()
        return
    _savefig(_out_path(args, "wkt"), title)
    print(f"wkt points: {len(point_x)} polygons: {n_poly} skipped: {skipped}")


def cmd_near(args: argparse.Namespace) -> None:
    """Filter lat/lon rows by haversine distance (no GeoSPARQL / QLever)."""
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "latlon.rq",
        limit=args.limit,
        timeout=args.timeout,
    )
    rows = require_rows(data, "near")
    pts, skipped = collect_points(rows)
    origin_lat, origin_lon, radius = args.lat, args.lon, args.km
    hits = []
    for p in pts:
        dist = haversine_km(origin_lat, origin_lon, p["_lat"], p["_lon"])
        if dist <= radius:
            p["_km"] = dist
            hits.append(p)
    hits.sort(key=lambda r: r["_km"])
    title = args.title or f"within {radius:g} km of {origin_lat:g},{origin_lon:g} (n={len(hits)})"
    pad = max(radius / EARTH_KM * 180 / math.pi * 1.4, 2.0)
    # longitude padding scales with cos(lat)
    coslat = max(0.2, math.cos(math.radians(origin_lat)))
    lon_pad = pad / coslat
    xlim = (max(-180, origin_lon - lon_pad), min(180, origin_lon + lon_pad))
    ylim = (max(-90, origin_lat - pad), min(90, origin_lat + pad))
    _, ax = _base_axes(title, coastlines=args.coastlines, xlim=xlim, ylim=ylim)
    cx, cy = circle_lonlat(origin_lat, origin_lon, radius)
    ax.plot(cx, cy, color="#3d6ea8", linewidth=1.0, zorder=1)
    ax.plot(origin_lon, origin_lat, "+", color="#1b3f6e", markersize=10, zorder=3)
    if hits:
        ax.scatter(
            [p["_lon"] for p in hits],
            [p["_lat"] for p in hits],
            s=18,
            alpha=0.7,
            c="#c23b22",
            linewidths=0,
            zorder=2,
        )
    _savefig(_out_path(args, "near"), title)
    print(f"within radius: {len(hits)} scanned: {len(pts)} skipped: {skipped}")
    if not hits:
        print("No points within radius.")
        return
    print("| km | lat | lon | s |")
    print("| --- | --- | --- | --- |")
    for p in hits[:25]:
        print(
            f"| {p['_km']:.1f} | {p['_lat']:.4f} | {p['_lon']:.4f} | {p.get('s') or ''} |"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map SPARQL spatial fields (portable; no QLever spatial functions)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_pts = sub.add_parser("points", help="lat/lon scatter")
    _add_io(p_pts, 4000)
    p_pts.set_defaults(func=cmd_points)
    p_box = sub.add_parser("boxes", help="schema:box rectangles")
    _add_io(p_box, 300)
    p_box.set_defaults(func=cmd_boxes)
    p_wkt = sub.add_parser("wkt", help="GeoSPARQL asWKT")
    _add_io(p_wkt, 80)
    p_wkt.set_defaults(func=cmd_wkt)
    p_near = sub.add_parser("near", help="Haversine filter around --lat --lon --km")
    _add_io(p_near, 8000)
    p_near.add_argument("--lat", type=float, required=True, help="Origin latitude")
    p_near.add_argument("--lon", type=float, required=True, help="Origin longitude")
    p_near.add_argument("--km", type=float, required=True, help="Radius kilometres")
    p_near.set_defaults(func=cmd_near)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
