"""Shared helpers for catalog-plot / catalog-map / forecast-inventory."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILLS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILLS_DIR.parent
SPARQL_CLI = REPO_ROOT / "skills" / "sparql" / "scripts" / "sparql_query.py"


def load_result(path: Path) -> dict[str, Any]:
    """Load SPARQL JSON written by sparql_query.py --format json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "rows" not in data:
        print(f"Error: {path} is not sparql_query.py JSON (need columns/rows)", file=sys.stderr)
        sys.exit(1)
    data.setdefault("columns", [])
    data.setdefault("count", len(data.get("rows") or []))
    return data


def run_sparql(
    endpoint: str,
    *,
    query_id: str | None = None,
    query_file: Path | None = None,
    limit: int | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Run the in-repo SPARQL CLI and parse JSON stdout."""
    if not SPARQL_CLI.is_file():
        print(f"Error: SPARQL CLI missing: {SPARQL_CLI}", file=sys.stderr)
        sys.exit(1)
    cmd = [
        "uv",
        "run",
        "python",
        str(SPARQL_CLI),
    ]
    if query_id:
        cmd += ["run", "--endpoint", endpoint, "--query", query_id]
    elif query_file:
        cmd += ["file", "--endpoint", endpoint, "--query-file", str(query_file)]
    else:
        print("Error: run_sparql needs query_id or query_file", file=sys.stderr)
        sys.exit(1)
    cmd += ["--format", "json", "--timeout", str(timeout)]
    if limit is not None:
        cmd += ["--limit", str(limit)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        print(f"Error: SPARQL CLI failed:\n{err}", file=sys.stderr)
        sys.exit(proc.returncode or 1)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("Error: SPARQL CLI did not return JSON", file=sys.stderr)
        print(proc.stdout[:500], file=sys.stderr)
        sys.exit(1)


def resolve_result(
    *,
    from_json: Path | None,
    endpoint: str | None,
    query_id: str | None = None,
    query_file: Path | None = None,
    limit: int | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Load --from-json or fetch via --endpoint."""
    if from_json:
        return load_result(from_json)
    if not endpoint:
        print("Error: need --from-json or --endpoint", file=sys.stderr)
        sys.exit(1)
    return run_sparql(
        endpoint,
        query_id=query_id,
        query_file=query_file,
        limit=limit,
        timeout=timeout,
    )


def default_png(mode: str) -> Path:
    """runs/<mode>-<utc>.png under the repo root."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO_ROOT / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{mode}-{stamp}.png"


def to_float(value: Any) -> float | None:
    """Parse a SPARQL literal to float; None if missing/unparseable."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def localname(uri: str | None) -> str:
    """Short label from a URI or raw string."""
    if not uri:
        return ""
    text = str(uri)
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    if "#" in text:
        text = text.rsplit("#", 1)[-1]
    return text or str(uri)


def require_rows(data: dict[str, Any], label: str) -> list[dict[str, Any]]:
    """Return rows or exit with an honest empty-result message."""
    rows = data.get("rows") or []
    if not rows:
        print(f"No rows for {label}. Nothing plotted.")
        sys.exit(0)
    return rows
