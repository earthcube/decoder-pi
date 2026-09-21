#!/usr/bin/env python3
"""List/plot EFI parquet from schema.org DataDownload URLs (portable SPARQL + HTTP)."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
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
# EFI issue and target times are UTC midnights. A lead that is not within
# this many seconds of a whole day is reported and left unbinned.
LEAD_TOLERANCE_SECONDS = 60
_ISO_DURATION = re.compile(
    r"^(?P<sign>-)?P"
    r"(?:(?P<weeks>\d+(?:\.\d+)?)W)?"
    r"(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)
_WORD_DURATION = re.compile(
    r"^(?P<sign>-)?\s*(?P<num>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>weeks?|days?|hours?|minutes?|seconds?)\s*$",
    re.IGNORECASE,
)
_PATH_FIELD = re.compile(r"(?:^|[/?&=])([A-Za-z0-9_]+)=([^/?&=]+)")


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


def pick_horizon_y(names: list[str], requested: str | None) -> str:
    """Horizon plots stored CRPS unless another score column is requested."""
    if requested:
        return pick_y_column(names, requested)
    if "crps" not in names:
        print(
            "Error: no crps column. Pass --y to plot another column at one lead.",
            file=sys.stderr,
        )
        sys.exit(1)
    return "crps"


def as_utc(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return None


def whole_lead_days(delta: timedelta) -> int | None:
    """Whole days between issue and target, or None if it is not a whole day."""
    seconds = delta.total_seconds()
    nearest = round(seconds / 86400.0)
    if abs(seconds - nearest * 86400.0) > LEAD_TOLERANCE_SECONDS:
        return None
    return int(nearest)


def _duration_seconds(text: str) -> float | None:
    """Parse an ISO-8601 or '<number> <unit>' duration to seconds."""
    iso = _ISO_DURATION.fullmatch(text.strip())
    if iso and any(iso.group(name) for name in ("weeks", "days", "hours", "minutes", "seconds")):
        sign = -1.0 if iso.group("sign") else 1.0
        seconds = 0.0
        if iso.group("weeks"):
            seconds += float(iso.group("weeks")) * 7 * 86400.0
        if iso.group("days"):
            seconds += float(iso.group("days")) * 86400.0
        if iso.group("hours"):
            seconds += float(iso.group("hours")) * 3600.0
        if iso.group("minutes"):
            seconds += float(iso.group("minutes")) * 60.0
        if iso.group("seconds"):
            seconds += float(iso.group("seconds"))
        return sign * seconds
    word = _WORD_DURATION.fullmatch(text.strip())
    if not word:
        return None
    sign = -1.0 if word.group("sign") else 1.0
    number = float(word.group("num"))
    unit = word.group("unit").lower()
    scale = {
        "week": 7 * 86400.0,
        "day": 86400.0,
        "hour": 3600.0,
        "minute": 60.0,
        "second": 1.0,
    }[unit.rstrip("s")]
    return sign * number * scale


def horizon_matches(value: object, delta: timedelta) -> bool:
    """True when a stored horizon equals datetime minus reference_datetime.

    Durations and unit-bearing strings use their own unit. A bare number is
    days, which is how EFI states a lead. Other numeric units are not guessed.
    """
    if value is None:
        return True
    expected = delta.total_seconds()
    if isinstance(value, timedelta):
        return abs(value.total_seconds() - expected) <= LEAD_TOLERANCE_SECONDS
    if isinstance(value, str):
        parsed = _duration_seconds(value)
        if parsed is None:
            try:
                value = float(value.strip())
            except ValueError:
                return False
        else:
            return abs(parsed - expected) <= LEAD_TOLERANCE_SECONDS
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return abs(float(value) * 86400.0 - expected) <= LEAD_TOLERANCE_SECONDS


def check_horizon_column(table) -> None:
    """Exit when a stored horizon column disagrees with the two timestamps."""
    names = table.column_names
    if "horizon" not in names:
        print("horizon_column: absent; lead is datetime minus reference_datetime")
        return
    if "datetime" not in names or "reference_datetime" not in names:
        return
    targets = table.column("datetime").to_pylist()
    issued = table.column("reference_datetime").to_pylist()
    stored = table.column("horizon").to_pylist()
    mismatches: list[str] = []
    checked = 0
    for target, ref, horizon in zip(targets, issued, stored):
        if horizon is None:
            continue
        target_utc = as_utc(target)
        ref_utc = as_utc(ref)
        if target_utc is None or ref_utc is None:
            continue
        checked += 1
        delta = target_utc - ref_utc
        if horizon_matches(horizon, delta):
            continue
        lead = whole_lead_days(delta)
        computed = f"{lead} days" if lead is not None else f"{delta.total_seconds():.0f} seconds"
        mismatches.append(
            f"target={target_utc.isoformat()} reference={ref_utc.isoformat()} "
            f"horizon={horizon!r} computed={computed}"
        )
        if len(mismatches) >= 3:
            break
    if checked == 0:
        print("horizon_column: all null; lead is datetime minus reference_datetime")
        return
    if mismatches:
        print(
            "Error: horizon column does not match datetime minus reference_datetime.",
            file=sys.stderr,
        )
        for line in mismatches:
            print(f"  {line}", file=sys.stderr)
        print("Nothing plotted.", file=sys.stderr)
        sys.exit(1)
    print(f"horizon_column: matches computed lead ({checked} non-null values)")


def path_fields(source: str) -> dict[str, str]:
    return {key: unquote(value) for key, value in _PATH_FIELD.findall(source)}


def numeric_y(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_scored(table, y_name: str, site: str | None) -> tuple[list[dict], Counter]:
    """Site-filtered numeric rows, with a whole-day lead when the span is exact."""
    names = table.column_names
    data = {name: table.column(name).to_pylist() for name in names}
    n = table.num_rows
    extra = [c for c in ("family", "pub_datetime", "model_id", "variable", "horizon") if c in names]
    sites = data["site_id"] if "site_id" in data else [None] * n
    stats: Counter = Counter()
    rows: list[dict] = []
    for i in range(n):
        site_i = sites[i]
        if site and site_i != site:
            stats["other_site"] += 1
            continue
        target = as_utc(data["datetime"][i])
        issued = as_utc(data["reference_datetime"][i])
        if target is None or issued is None:
            stats["missing_time"] += 1
            continue
        yv = numeric_y(data[y_name][i])
        if yv is None:
            stats["nonnumeric_y"] += 1
            continue
        lead = whole_lead_days(target - issued)
        row = {
            "target": target,
            "issued": issued,
            "lead": lead,
            "y": yv,
            "site": "" if site_i is None else str(site_i),
        }
        for column in extra:
            row[column] = data[column][i]
        if lead is None:
            stats["fractional"] += 1
        rows.append(row)
    return rows, stats


def group_by_lead(rows: list[dict]) -> tuple[dict[int, list[dict]], list[dict]]:
    by_lead: dict[int, list[dict]] = defaultdict(list)
    fractional: list[dict] = []
    for row in rows:
        if row["lead"] is None:
            fractional.append(row)
        else:
            by_lead[row["lead"]].append(row)
    return by_lead, fractional


def duplicate_targets(group: list[dict]) -> int:
    counts = Counter((row["site"], row["target"]) for row in group)
    return sum(1 for count in counts.values() if count > 1)


def print_lead_table(by_lead: dict[int, list[dict]], fractional: int) -> None:
    print("| lead_days | scored_rows | sites | target_dates | duplicate_targets |")
    print("| --- | --- | --- | --- | --- |")
    for lead in sorted(by_lead):
        group = by_lead[lead]
        sites = len({row["site"] for row in group})
        targets = len({(row["site"], row["target"]) for row in group})
        print(
            f"| {lead} | {len(group)} | {sites} | {targets} | {duplicate_targets(group)} |"
        )
    print(f"fractional_scored_rows: {fractional}")


def fmt_value(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def refuse_duplicate_targets(group: list[dict], lead: int, y_name: str) -> None:
    """One target date at one lead must be one stored score."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in group:
        buckets[(row["site"], row["target"])].append(row)
    collisions = [(key, rows) for key, rows in buckets.items() if len(rows) > 1]
    if not collisions:
        return
    n = len(collisions)
    noun = "target date" if n == 1 else "target dates"
    verb = "has" if n == 1 else "have"
    print(
        f"Error: lead {lead} days is not one score per target date "
        f"({n} {noun} {verb} more than one row).",
        file=sys.stderr,
    )
    for (site, target), rows in collisions[:3]:
        print(
            f"site {site or '(none)'} target {target.date().isoformat()} has {len(rows)} scored rows.",
            file=sys.stderr,
        )
        varying = []
        for key in ("issued", "pub_datetime", "family", "model_id", "variable", "horizon", "y"):
            if not any(key in row for row in rows):
                continue
            values = [row.get(key) for row in rows]
            if key == "y" or len({repr(value) for value in values}) > 1:
                varying.append(key)
        for row in rows:
            bits = [
                f"{y_name if key == 'y' else key}={fmt_value(row.get(key))}"
                for key in varying
            ]
            print("  " + " ".join(bits), file=sys.stderr)
    if len(collisions) > 3:
        print(f"  and {len(collisions) - 3} more target dates.", file=sys.stderr)
    print(
        "Rows that share a target date and a lead are left as separate scores. Nothing plotted.",
        file=sys.stderr,
    )
    sys.exit(1)


def require_one_value(rows: list[dict], column: str) -> None:
    if not rows or column not in rows[0]:
        return
    values = []
    for row in rows:
        value = row.get(column)
        if value in (None, "") or value in values:
            continue
        values.append(value)
    if len(values) <= 1:
        return
    shown = ", ".join(str(value) for value in values[:8])
    print(
        f"Error: {column} has {len(values)} values at this lead ({shown}). "
        "One horizon series uses one model and one variable.",
        file=sys.stderr,
    )
    sys.exit(1)


def print_identity(rows: list[dict], source: str, column: str) -> None:
    if rows and column in rows[0]:
        values = []
        for row in rows:
            value = row.get(column)
            if value in (None, "") or value in values:
                continue
            values.append(value)
        if not values:
            shown = "(all null)"
        else:
            shown = ", ".join(str(value) for value in values[:6])
            if len(values) > 6:
                shown += f" (+{len(values) - 6})"
        print(f"{column}: {shown}")
        return
    found = path_fields(source).get(column)
    if found:
        print(f"{column}: {found} (from source path)")
    else:
        print(f"{column}: (not in file)")


def series_segments(
    pts: list[tuple[datetime, float]],
) -> tuple[list[list[tuple[datetime, float]]], int, float | None]:
    """Split a fixed-lead series where a gap is longer than 1.5 times the median step."""
    pts = sorted(pts, key=lambda point: point[0])
    if len(pts) < 2:
        return [pts], 0, None
    diffs = [(b[0] - a[0]).total_seconds() for a, b in zip(pts, pts[1:])]
    positive = sorted(diff for diff in diffs if diff > 0)
    if not positive:
        return [pts], 0, None
    step = positive[len(positive) // 2]
    groups: list[list[tuple[datetime, float]]] = [[pts[0]]]
    gaps = 0
    for cur, diff in zip(pts[1:], diffs):
        if diff > step * 1.5:
            gaps += 1
            groups.append([cur])
        else:
            groups[-1].append(cur)
    return groups, gaps, step


def fmt_step_days(step_seconds: float | None) -> str:
    if step_seconds is None:
        return "(one target date)"
    nearest = round(step_seconds / 86400.0)
    if abs(step_seconds - nearest * 86400.0) <= LEAD_TOLERANCE_SECONDS:
        return str(int(nearest))
    return f"{step_seconds / 86400.0:.2f}"


def lead_phrase(leads: list[int]) -> str:
    ordered = sorted(leads)
    if len(ordered) <= 6:
        if len(ordered) == 1:
            body = str(ordered[0])
        else:
            body = ", ".join(str(lead) for lead in ordered[:-1]) + f" and {ordered[-1]}"
        label = "lead" if len(ordered) == 1 else "leads"
        return f"{len(ordered)} whole-day {label} ({body} days)"
    return f"{len(ordered)} whole-day leads ({ordered[0]} to {ordered[-1]} days)"


def mixed_lead_notice(table, y_name: str, site: str | None) -> str | None:
    """Tell plot users when the line stacks more than one lead on the target date."""
    names = table.column_names
    if "reference_datetime" not in names or "datetime" not in names or y_name not in names:
        return None
    rows, _stats = collect_scored(table, y_name, site)
    whole = sorted({row["lead"] for row in rows if row["lead"] is not None})
    fractional = sum(1 for row in rows if row["lead"] is None)
    if len(whole) <= 1 and fractional == 0:
        return None
    parts = []
    if whole:
        parts.append(lead_phrase(whole))
    if fractional:
        noun = "row" if fractional == 1 else "rows"
        parts.append(f"{fractional} fractional lead {noun}")
    joined = " and ".join(parts)
    return (
        f"notice: plotted rows use {joined}. "
        "horizon --lead N keeps one whole-day lead and one score per target date."
    )


def open_parquet(args: argparse.Namespace) -> tuple[str, Path] | None:
    """Return (source label, local parquet). None when no SPARQL URL matched."""
    if args.from_parquet:
        local = args.from_parquet
        if not local.is_file():
            print(f"Error: parquet not found: {local}", file=sys.stderr)
            sys.exit(1)
        return str(local), local
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
        matches = [str(row.get("url") or "") for row in rows if str(row.get("url") or "")]
        if needle:
            matches = [item for item in matches if needle in item.lower()]
        if not matches:
            print("No parquet URL matched. Use list --contains … first.")
            return None
        url = matches[0]
        print(f"using url: {url}")
        if len(matches) > 1:
            print(f"( {len(matches)} matches; pass --contains to pick another )")
    return resolve_parquet_object(url, args.timeout)


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
    opened = open_parquet(args)
    if opened is None:
        return
    source, local = opened
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
    notice = mixed_lead_notice(table, y_name, args.site)
    if notice:
        print(notice)
    print(f"Wrote {out}")
    print(f"source: {source}")
    print(f"y: {y_name} plotted_rows: {n_plotted}")


def cmd_horizon(args: argparse.Namespace) -> None:
    opened = open_parquet(args)
    if opened is None:
        return
    source, local = opened
    table = pq.read_table(local)
    names = table.column_names
    print("columns:", ", ".join(names))
    print(f"rows: {table.num_rows}")
    if "datetime" not in names or "reference_datetime" not in names:
        print(
            "Error: a lead needs both datetime and reference_datetime.",
            file=sys.stderr,
        )
        sys.exit(1)
    y_name = pick_horizon_y(names, args.y)
    check_horizon_column(table)
    rows, stats = collect_scored(table, y_name, args.site)
    by_lead, fractional = group_by_lead(rows)
    print(f"filter_site: {args.site or '(all)'}")
    print(f"null_or_nonnumeric_y: {stats['nonnumeric_y']}")
    print(f"rows_missing_datetime_or_reference: {stats['missing_time']}")
    if not rows:
        print("No numeric rows to summarize after filters.")
        return
    if args.lead is None:
        print("No --lead given. Scored rows by whole-day lead (nothing plotted):")
        print_lead_table(by_lead, len(fractional))
        return
    if args.lead not in by_lead:
        print(f"No scored rows at lead {args.lead} days.")
        print_lead_table(by_lead, len(fractional))
        return

    selected = by_lead[args.lead]
    refuse_duplicate_targets(selected, args.lead, y_name)
    require_one_value(selected, "model_id")
    require_one_value(selected, "variable")

    series: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for row in selected:
        series[row["site"]].append((row["target"], row["y"]))
    keys = sorted(series)
    plotted = keys if args.site else keys[:MAX_SITES]
    if len(keys) > len(plotted):
        print(f"plotted {len(plotted)} of {len(keys)} sites (use --site)")

    other_rows = sum(len(group) for lead, group in by_lead.items() if lead != args.lead)
    print(f"lead_days: {args.lead}")
    print(f"scored_rows_at_lead: {len(selected)}")
    print(f"other_whole_day_scored_rows: {other_rows}")
    print(f"fractional_scored_rows: {len(fractional)}")
    print_identity(selected, source, "model_id")
    print_identity(selected, source, "variable")
    print_identity(selected, source, "family")
    duration = path_fields(source).get("duration")
    if duration:
        print(f"duration: {duration} (from source path)")
    if args.site:
        print(f"site: {args.site}")

    title = args.title or f"{y_name} vs target date, lead {args.lead} days"
    if args.site:
        title = args.title or f"{title} ({args.site})"
    fig, ax = plt.subplots(figsize=(10, 4.8))
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    gap_notes = []
    for index, key in enumerate(plotted):
        pts = series[key]
        groups, gaps, step = series_segments(pts)
        color = "#3d6ea8" if len(plotted) == 1 else cycle[index % len(cycle)]
        for seg_i, group in enumerate(groups):
            ax.plot(
                [point[0] for point in group],
                [point[1] for point in group],
                color=color,
                marker="o",
                linewidth=1.1,
                label=key if seg_i == 0 and len(plotted) > 1 else "_nolegend_",
            )
        gap_notes.append(
            f"site {key or '(none)'}: targets {len(pts)} "
            f"step_days {fmt_step_days(step)} gaps {gaps}"
        )
    if len(plotted) > 1:
        ax.legend(fontsize=7, ncol=2)
    ax.set_xlabel("target datetime")
    ax.set_ylabel(y_name)
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.4)
    fig.autofmt_xdate()
    out = args.output or default_png(f"horizon-{y_name}-{args.lead}d")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    values = [row["y"] for row in selected if row["site"] in plotted]
    print(f"y_min: {min(values):.6g}")
    print(f"y_max: {max(values):.6g}")
    for note in gap_notes:
        print(note)
    print(f"Wrote {out}")
    print(f"source: {source}")
    print(f"y: {y_name} lead_days: {args.lead} plotted_rows: {len(values)}")


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

    p_horizon = sub.add_parser(
        "horizon",
        help="Plot one whole-day lead so each target date has one score",
    )
    p_horizon.add_argument("--endpoint")
    p_horizon.add_argument("--from-json", type=Path, dest="from_json")
    p_horizon.add_argument("--url", help="s3://anonymous@… or https://… parquet prefix/object")
    p_horizon.add_argument(
        "--from-parquet",
        type=Path,
        dest="from_parquet",
        help="Local parquet file (skip download)",
    )
    p_horizon.add_argument("--contains", default=None, help="Pick first SPARQL URL containing this")
    p_horizon.add_argument(
        "--y",
        default=None,
        help="Score column (default: crps). This does not recompute the score.",
    )
    p_horizon.add_argument("--site", default=None, help="Filter to one site_id")
    p_horizon.add_argument(
        "--lead",
        type=int,
        default=None,
        help="Whole days from reference_datetime to datetime. Omit to list leads and not plot.",
    )
    p_horizon.add_argument("-o", "--output", type=Path)
    p_horizon.add_argument("--title", default=None)
    p_horizon.add_argument("--limit", type=int, default=80)
    p_horizon.add_argument("--timeout", type=int, default=60)
    p_horizon.set_defaults(func=cmd_horizon)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
