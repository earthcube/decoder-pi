#!/usr/bin/env python3
"""List/plot EFI parquet from schema.org DataDownload URLs (portable SPARQL + HTTP)."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from collections import defaultdict
from urllib.request import Request, urlopen

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

SHARED = Path(__file__).resolve().parents[2] / "_shared"
sys.path.insert(0, str(SHARED))
from cli import default_png, require_rows, resolve_result  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
QUERIES = SKILL_ROOT / "queries"
S3_NS = "http://s3.amazonaws.com/doc/2006-03-01/"
UA = "decoder-pi-forecast-parquet/1.0"
Y_PREFER = ("crps", "mean", "median", "observation", "prediction")
MAX_SITES = 8
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024


def _http_get(url: str, timeout: int) -> bytes:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        print(f"Error: download exceeded {MAX_DOWNLOAD_BYTES} bytes: {url}", file=sys.stderr)
        sys.exit(1)
    return data


def parse_osn_url(url: str) -> tuple[str, str, str] | None:
    """Return (endpoint_host, bucket, key_or_prefix) for EFI OSN-style URLs."""
    raw = (url or "").strip()
    if not raw:
        return None
    if raw.startswith("s3://"):
        rest = raw[5:]
        host = ""
        if "?" in rest:
            rest, query = rest.split("?", 1)
            host = (parse_qs(query).get("endpoint_override") or [""])[0]
        if "@" in rest.split("/", 1)[0]:
            _creds, rest = rest.split("@", 1)
        bucket, _, key = rest.partition("/")
        if not host or not bucket:
            return None
        return host, bucket, key
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https") and parsed.netloc and parsed.path:
        parts = parsed.path.lstrip("/").split("/", 1)
        if len(parts) != 2:
            return None
        return parsed.netloc, parts[0], parts[1]
    return None


def list_parquet_keys(host: str, bucket: str, prefix: str, timeout: int) -> list[tuple[str, int]]:
    """List objects under prefix; return (key, size) for .parquet files."""
    prefix = prefix.rstrip("/") + "/"
    list_url = (
        f"https://{host}/{bucket}?list-type=2&prefix={prefix}&max-keys=25"
    )
    xml = _http_get(list_url, timeout).decode("utf-8", errors="replace")
    root = ET.fromstring(xml)
    out: list[tuple[str, int]] = []
    for contents in root.findall(f"{{{S3_NS}}}Contents"):
        key_el = contents.find(f"{{{S3_NS}}}Key")
        size_el = contents.find(f"{{{S3_NS}}}Size")
        if key_el is None or not (key_el.text or "").endswith(".parquet"):
            continue
        size = int(size_el.text) if size_el is not None and size_el.text else 0
        out.append((key_el.text or "", size))
    return out


def resolve_parquet_object(url: str, timeout: int) -> tuple[str, Path]:
    """Download a parquet object; return (http_url, local_path)."""
    parsed = parse_osn_url(url)
    if parsed is None:
        print(f"Error: unsupported parquet URL: {url}", file=sys.stderr)
        sys.exit(1)
    host, bucket, key = parsed
    if key.endswith(".parquet"):
        http_url = f"https://{host}/{bucket}/{key}"
    else:
        keys = list_parquet_keys(host, bucket, key, timeout)
        if not keys:
            print(f"Error: no .parquet objects under {url}", file=sys.stderr)
            sys.exit(1)
        keys.sort(key=lambda t: t[1])
        key, size = keys[0]
        if size > MAX_DOWNLOAD_BYTES:
            print(f"Error: parquet {key} is {size} bytes (cap {MAX_DOWNLOAD_BYTES})", file=sys.stderr)
            sys.exit(1)
        http_url = f"https://{host}/{bucket}/{key}"
        print(f"selected object: {key} ({size} bytes)")
    dest = Path("/tmp") / ("decoder-pi-" + key.replace("/", "_"))
    dest.write_bytes(_http_get(http_url, timeout))
    return http_url, dest


def pick_y_column(names: list[str], requested: str | None) -> str:
    if requested:
        if requested not in names:
            print(f"Error: column {requested!r} not in {names}", file=sys.stderr)
            sys.exit(1)
        return requested
    for cand in Y_PREFER:
        if cand in names:
            return cand
    print(f"Error: no plottable column among {names}", file=sys.stderr)
    sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    data = resolve_result(
        from_json=args.from_json,
        endpoint=args.endpoint,
        query_file=QUERIES / "parquet_urls.rq",
        limit=args.limit or 50,
        timeout=args.timeout,
    )
    rows = require_rows(data, "parquet urls")
    needle = (args.contains or "").lower()
    shown = 0
    print("| url |")
    print("| --- |")
    for row in rows:
        url = str(row.get("url") or "")
        if needle and needle not in url.lower():
            continue
        print(f"| {url} |")
        shown += 1
    print(f"urls: {shown} (of {len(rows)} distinct parquet downloads)")


def cmd_plot(args: argparse.Namespace) -> None:
    if args.from_parquet:
        local = args.from_parquet
        if not local.is_file():
            print(f"Error: parquet not found: {local}", file=sys.stderr)
            sys.exit(1)
        source = str(local)
    else:
        url = args.url
        if not url:
            data = resolve_result(
                from_json=args.from_json,
                endpoint=args.endpoint,
                query_file=QUERIES / "parquet_urls.rq",
                limit=args.limit or 80,
                timeout=args.timeout,
            )
            rows = require_rows(data, "parquet urls")
            needle = (args.contains or "").lower()
            matches = [str(r.get("url") or "") for r in rows if str(r.get("url") or "")]
            if needle:
                matches = [u for u in matches if needle in u.lower()]
            if not matches:
                print("No parquet URL matched. Use list --contains … first.")
                return
            url = matches[0]
            print(f"using url: {url}")
            if len(matches) > 1:
                print(f"( {len(matches)} matches; pass --contains to pick another )")
        source, local = resolve_parquet_object(url, args.timeout)

    table = pq.read_table(local)
    names = table.column_names
    print("columns:", ", ".join(names))
    print(f"rows: {table.num_rows}")
    y_name = pick_y_column(names, args.y)
    if "datetime" not in names:
        print("Error: parquet has no datetime column; cannot plot a series.", file=sys.stderr)
        sys.exit(1)

    times = table.column("datetime").to_pylist()
    values = table.column(y_name).to_pylist()
    sites = table.column("site_id").to_pylist() if "site_id" in names else [None] * len(times)
    series: dict[str, list[tuple]] = defaultdict(list)
    for t, v, site in zip(times, values, sites):
        if t is None or v is None:
            continue
        try:
            yv = float(v)
        except (TypeError, ValueError):
            continue
        if args.site and site != args.site:
            continue
        key = str(site) if site is not None else ""
        series[key].append((t, yv))
    if not series:
        print("No numeric rows to plot after filters.")
        return

    title = args.title or f"{y_name} vs datetime"
    fig, ax = plt.subplots(figsize=(10, 4.8))
    keys = list(series.keys())
    if len(keys) > 1 and not args.site:
        plotted = keys[:MAX_SITES]
        for key in plotted:
            pts = sorted(series[key], key=lambda p: p[0])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], label=key, linewidth=1.0)
        if len(keys) > MAX_SITES:
            print(f"plotted {MAX_SITES} of {len(keys)} sites (use --site)")
        ax.legend(fontsize=7, ncol=2)
        n_plotted = sum(len(series[k]) for k in plotted)
    else:
        pts = sorted(next(iter(series.values())), key=lambda p: p[0])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#3d6ea8", linewidth=1.1)
        n_plotted = len(pts)
    ax.set_xlabel("datetime")
    ax.set_ylabel(y_name)
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.4)
    fig.autofmt_xdate()
    out = args.output or default_png(f"parquet-{y_name}")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Wrote {out}")
    print(f"source: {source}")
    print(f"y: {y_name} plotted_rows: {n_plotted}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot EFI parquet series found via SPARQL DataDownload URLs"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List parquet contentUrls from the graph")
    p_list.add_argument("--endpoint")
    p_list.add_argument("--from-json", type=Path, dest="from_json")
    p_list.add_argument("--contains", default=None, help="Substring filter on URL")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--timeout", type=int, default=60)
    p_list.set_defaults(func=cmd_list)

    p_plot = sub.add_parser("plot", help="Download one parquet and plot a series")
    p_plot.add_argument("--endpoint")
    p_plot.add_argument("--from-json", type=Path, dest="from_json")
    p_plot.add_argument("--url", help="s3://anonymous@… or https://… parquet prefix/object")
    p_plot.add_argument(
        "--from-parquet",
        type=Path,
        dest="from_parquet",
        help="Local parquet file (skip download)",
    )
    p_plot.add_argument("--contains", default=None, help="Pick first SPARQL URL containing this")
    p_plot.add_argument("--y", default=None, help="Column to plot (default: crps, else mean)")
    p_plot.add_argument("--site", default=None, help="Filter to one site_id")
    p_plot.add_argument("-o", "--output", type=Path)
    p_plot.add_argument("--title", default=None)
    p_plot.add_argument("--limit", type=int, default=80)
    p_plot.add_argument("--timeout", type=int, default=60)
    p_plot.set_defaults(func=cmd_plot)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
