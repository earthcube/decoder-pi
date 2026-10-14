#!/usr/bin/env python3
"""
Download IODP / GCR datasets listed in a text file, one URL at a time.

Handles three kinds of URLs:
  1. Zenodo DOIs (https://doi.org/10.5281/zenodo.NNNN) -> looks up the record via
     the Zenodo API and downloads every file in it, verifying MD5 checksums.
  2. Direct file links (.zip, .pdf, .csv, ...) -> downloaded as-is.
  3. Anything else (web pages / JS apps) -> saved as an HTML snapshot.

Features: skips files already downloaded (checksum/size match), retries with
backoff, honors HTTP 429 Retry-After, optional size cap, dry-run mode, and a
manifest.csv describing everything fetched.

Usage:
    pip install requests
    python download_gcr_data.py urls.txt
    python download_gcr_data.py urls.txt --out data --max-size-gb 2 --dry-run
"""

import argparse
import csv
import hashlib
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

ZENODO_API = "https://zenodo.org/api/records/{}"
ZENODO_DOI_RE = re.compile(r"10\.5281/zenodo\.(\d+)", re.I)
DIRECT_EXTS = {".zip", ".pdf", ".csv", ".txt", ".xlsx", ".xls", ".json",
               ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".gz", ".tar", ".ris"}
CHUNK = 1024 * 1024  # 1 MiB

session = requests.Session()
session.headers["User-Agent"] = "gcr-data-downloader/1.0 (research use)"


# ---------------------------------------------------------------- helpers
def read_urls(path):
    urls = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def slugify(text, maxlen=80):
    text = re.sub(r"[^\w\-. ]+", "", text).strip().replace(" ", "_")
    return text[:maxlen] or "untitled"


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def request(method, url, retries=5, **kw):
    """HTTP request with retry/backoff; respects 429 Retry-After."""
    delay = 5
    for attempt in range(1, retries + 1):
        try:
            r = session.request(method, url, timeout=60, **kw)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", delay))
                print(f"    rate-limited; sleeping {wait}s")
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"server error {r.status_code}")
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            if attempt == retries:
                raise
            print(f"    {e} (attempt {attempt}/{retries}); retrying in {delay}s")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"giving up on {url}")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def stream_to_file(url, dest, expected_size=None, expected_md5=None):
    """Download url -> dest via a .part file. Returns 'downloaded' or 'skipped'."""
    if dest.exists():
        if expected_md5 and md5_of(dest) == expected_md5:
            return "skipped"
        if not expected_md5 and expected_size and dest.stat().st_size == expected_size:
            return "skipped"

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    r = request("GET", url, stream=True)
    r.raise_for_status()
    total = expected_size or int(r.headers.get("Content-Length", 0)) or None
    done, last = 0, time.time()
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(CHUNK):
            f.write(chunk)
            done += len(chunk)
            if time.time() - last > 2:
                pct = f" ({done / total:.0%})" if total else ""
                print(f"    {human(done)}{pct}", end="\r", flush=True)
                last = time.time()
    print(" " * 40, end="\r")

    if expected_md5 and md5_of(tmp) != expected_md5:
        tmp.unlink()
        raise ValueError(f"MD5 mismatch for {dest.name}")
    tmp.replace(dest)
    return "downloaded"


# ---------------------------------------------------------------- handlers
def resolve_zenodo_id(url):
    """Return Zenodo record id from a DOI/record URL, following redirects if needed."""
    m = ZENODO_DOI_RE.search(url) or re.search(r"zenodo\.org/records?/(\d+)", url)
    if m:
        return m.group(1)
    r = request("HEAD", url, allow_redirects=True)
    m = re.search(r"/records?/(\d+)", r.url)
    return m.group(1) if m else None


def handle_zenodo(url, out, args, manifest):
    rec_id = resolve_zenodo_id(url)
    r = request("GET", ZENODO_API.format(rec_id))
    if r.status_code == 404:
        # DOI suffix may be a concept id; follow the DOI redirect to the real record
        r2 = request("HEAD", url, allow_redirects=True)
        m = re.search(r"/records?/(\d+)", r2.url)
        if not m:
            raise ValueError(f"cannot resolve Zenodo record for {url}")
        rec_id = m.group(1)
        r = request("GET", ZENODO_API.format(rec_id))
    r.raise_for_status()
    rec = r.json()

    title = rec.get("metadata", {}).get("title", f"zenodo_{rec_id}")
    folder = out / f"{rec_id}_{slugify(title)}"
    files = rec.get("files", [])
    total = sum(f.get("size", 0) for f in files)
    print(f"  '{title}' - {len(files)} file(s), {human(total)}")

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "zenodo_record.json").write_text(r.text, encoding="utf-8")

    for f in files:
        name = f.get("key") or f.get("filename")
        size = f.get("size", 0)
        md5 = (f.get("checksum") or "").replace("md5:", "") or None
        link = (f.get("links", {}).get("content")
                or f.get("links", {}).get("self")
                or f"https://zenodo.org/records/{rec_id}/files/{name}?download=1")
        row = dict(source_url=url, record_id=rec_id, title=title, file=name,
                   size_bytes=size, md5=md5 or "", path=str(folder / name), status="")

        if args.max_size_gb and size > args.max_size_gb * 1024**3:
            row["status"] = "skipped (over size cap)"
            print(f"    - {name} [{human(size)}] skipped: over --max-size-gb")
        elif args.dry_run:
            row["status"] = "dry-run"
            print(f"    - {name} [{human(size)}]")
        else:
            print(f"    - {name} [{human(size)}]")
            row["status"] = stream_to_file(link, folder / name, size, md5)
            print(f"      {row['status']}")
            time.sleep(args.delay)
        manifest.append(row)


def handle_direct(url, out, args, manifest):
    name = unquote(Path(urlparse(url).path).name)
    dest = out / "direct" / name
    row = dict(source_url=url, record_id="", title=name, file=name,
               size_bytes="", md5="", path=str(dest), status="")
    if args.dry_run:
        row["status"] = "dry-run"
    else:
        row["status"] = stream_to_file(url, dest)
        row["size_bytes"] = dest.stat().st_size
    print(f"  {name}: {row['status']}")
    manifest.append(row)


def handle_page(url, out, args, manifest):
    p = urlparse(url)
    name = slugify(f"{p.netloc}{p.path}".rstrip("/")) + ".html"
    dest = out / "page_snapshots" / name
    row = dict(source_url=url, record_id="", title="web page snapshot", file=name,
               size_bytes="", md5="", path=str(dest), status="")
    if args.dry_run:
        row["status"] = "dry-run"
    else:
        r = request("GET", url)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        row["size_bytes"] = len(r.content)
        row["status"] = "saved snapshot (interactive site - browse manually for data)"
    print(f"  {row['status']}")
    manifest.append(row)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url_file", help="text file with one URL per line")
    ap.add_argument("--out", default="gcr_downloads", help="output directory")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds to pause between files (be polite to Zenodo)")
    ap.add_argument("--max-size-gb", type=float, default=None,
                    help="skip individual files larger than this")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be downloaded, without downloading")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    urls = read_urls(args.url_file)
    manifest, failures = [], []

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            ext = Path(urlparse(url).path).suffix.lower()
            if ZENODO_DOI_RE.search(url) or "zenodo.org/record" in url:
                handle_zenodo(url, out, args, manifest)
            elif ext in DIRECT_EXTS:
                handle_direct(url, out, args, manifest)
            else:
                handle_page(url, out, args, manifest)
        except Exception as e:  # keep going; report at the end
            print(f"  FAILED: {e}")
            failures.append((url, str(e)))
            manifest.append(dict(source_url=url, record_id="", title="", file="",
                                 size_bytes="", md5="", path="", status=f"FAILED: {e}"))
        time.sleep(args.delay)

    mpath = out / "manifest.csv"
    with open(mpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source_url", "record_id", "title", "file",
                                          "size_bytes", "md5", "path", "status"])
        w.writeheader()
        w.writerows(manifest)

    print(f"\nDone. Manifest: {mpath}")
    if failures:
        print(f"{len(failures)} URL(s) failed:")
        for u, e in failures:
            print(f"  {u}\n    {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
