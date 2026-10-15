#!/usr/bin/env python3
"""Python fallback for sparqld: load RDF files (folder, file, or URL) into an
in-memory pyoxigraph store (rdflib if pyoxigraph is missing) and run SPARQL.

  local_sparql.py SOURCE [SOURCE...] (-q 'SPARQL' | -f query.rq) [--format tsv|json]
  local_sparql.py SOURCE --serve [--port 7737]   # read-only SPARQL endpoint (pyoxigraph)
SOURCE: directory (recursed), file, or http(s) URL. .gz is decompressed.
"""
import argparse, gzip, io, json, os, sys, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXT = {".nq": "application/n-quads", ".nt": "application/n-triples",
       ".ttl": "text/turtle", ".trig": "application/trig",
       ".jsonld": "application/ld+json", ".json": "application/ld+json",
       ".rdf": "application/rdf+xml", ".owl": "application/rdf+xml"}
RDFLIB_FMT = {"application/n-quads": "nquads", "application/n-triples": "nt",
              "text/turtle": "turtle", "application/trig": "trig",
              "application/ld+json": "json-ld", "application/rdf+xml": "xml"}

def _mime(name):
    n = name[:-3] if name.endswith(".gz") else name
    return EXT.get(os.path.splitext(n)[1].lower())

def _read(src):
    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src) as r:
            data = r.read()
    else:
        with open(src, "rb") as f:
            data = f.read()
    return gzip.decompress(data) if src.endswith(".gz") else data

def sources(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for fn in sorted(files):
                    if _mime(fn):
                        yield os.path.join(root, fn)
        else:
            yield p

def load(paths):
    try:
        import pyoxigraph as ox
        store, eng = ox.Store(), "pyoxigraph"
    except ImportError:
        import rdflib
        store, eng = rdflib.Dataset(default_union=True), "rdflib"
    for s in sources(paths):
        mime = _mime(urllib.parse.urlparse(s).path)
        if not mime:
            print(f"skip (unknown format): {s}", file=sys.stderr); continue
        data = _read(s)
        if eng == "pyoxigraph":
            import pyoxigraph as ox
            fmt = ox.RdfFormat.from_media_type(mime)
            kw = {} if fmt.supports_datasets else {"to_graph": ox.NamedNode(
                s if "://" in s else "file://" + os.path.abspath(s))}
            base = s if "://" in s else "file://" + os.path.abspath(s)
            try:
                store.bulk_load(io.BytesIO(data), format=fmt, base_iri=base, **kw)
            except SyntaxError as e:  # e.g. remote JSON-LD @context oxigraph can't fetch
                print(f"pyoxigraph failed on {s}: {e}; retrying with rdflib", file=sys.stderr)
                import rdflib
                g = rdflib.Dataset(); g.parse(data=data, format=RDFLIB_FMT[mime], publicID=base)
                store.bulk_load(io.BytesIO(g.serialize(format="nquads").encode()),
                                format=ox.RdfFormat.N_QUADS)
        else:
            store.parse(data=data, format=RDFLIB_FMT[mime])
    return store, eng

def query(store, eng, q, fmt="tsv"):
    if eng == "pyoxigraph":
        import pyoxigraph as ox
        res = store.query(q, use_default_graph_as_union=True)
        f = ox.QueryResultsFormat.TSV if fmt == "tsv" else ox.QueryResultsFormat.JSON
        return res.serialize(format=f).decode()
    res = store.query(q)
    return res.serialize(format="csv" if fmt == "tsv" else "json").decode()

def serve(store, port):
    import pyoxigraph as ox
    class H(BaseHTTPRequestHandler):
        def _run(self, q):
            if not q:
                self.send_response(400); self.end_headers(); return
            try:
                out = store.query(q, use_default_graph_as_union=True)
                acc = self.headers.get("Accept", "")
                f, ct = ((ox.QueryResultsFormat.TSV, "text/tab-separated-values")
                         if "tab-separated" in acc else
                         (ox.QueryResultsFormat.JSON, "application/sparql-results+json"))
                body = out.serialize(format=f)
                self.send_response(200); self.send_header("Content-Type", ct)
            except Exception as e:  # SPARQL Update and syntax errors land here
                body = str(e).encode(); self.send_response(400)
            self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._run(qs.get("query", [None])[0])
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            ct = self.headers.get("Content-Type", "")
            q = raw if "sparql-query" in ct else urllib.parse.parse_qs(raw).get("query", [None])[0]
            self._run(q)
    print(f"read-only SPARQL at http://127.0.0.1:{port}/", file=sys.stderr)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="+")
    ap.add_argument("-q", "--query"); ap.add_argument("-f", "--file")
    ap.add_argument("--format", default="tsv", choices=["tsv", "json"])
    ap.add_argument("--serve", action="store_true"); ap.add_argument("--port", type=int, default=7737)
    a = ap.parse_args()
    t = time.time(); store, eng = load(a.source)
    print(f"[{eng}] loaded {len(store)} quads in {time.time()-t:.1f}s", file=sys.stderr)
    if a.serve:
        if eng != "pyoxigraph": sys.exit("--serve needs pyoxigraph")
        serve(store, a.port); return
    q = a.query or (open(a.file).read() if a.file else None)
    if not q: sys.exit("give -q or -f")
    t = time.time(); print(query(store, eng, q, a.format), end="")
    print(f"query {time.time()-t:.2f}s", file=sys.stderr)

if __name__ == "__main__":
    main()
