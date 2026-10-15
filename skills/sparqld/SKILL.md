---
name: sparqld
description: >
  Serve a local directory of RDF files (JSON-LD, YAML-LD, Markdown-LD front matter,
  Turtle/N-Triples/N-Quads) as a live, read-only SPARQL endpoint with sparqld, then
  query it. Use when the user wants to query schema.org JSON-LD harvested to disk,
  check local records before loading them into QLever/Oxigraph, or inspect a
  folder of linked-data files. Triggers: sparqld, query these JSON-LD files,
  local RDF folder, /skill:sparqld.
  Not for: remote triplestores such as GeoCODES QLever (use the sparql skill),
  SPARQL Update, SHACL validation.
license: Apache-2.0
compatibility: sparqld >= 0.1.4 (Rust, rustc >= 1.88) + optional sq; fallback python3 + pyoxigraph (or rdflib) via scripts/local_sparql.py
metadata:
  project: decoder-pi
  version: "0.1"
  author: decoder-pi (adapted from iolanta-tech/sparqld skills/sparqld, Apache-2.0 OR MIT)
  source: https://github.com/iolanta-tech/sparqld
---

# sparqld (local files as a SPARQL endpoint)

sparqld watches a directory and serves its RDF files read-only at
`http://127.0.0.1:7737/`. Files stay the source of truth; edits are live.

## When to use this vs `sparql`

| Data lives in... | Skill |
|---|---|
| Remote endpoint (GeoCODES QLever deepoceans, Oxigraph) | `sparql` |
| Files on disk (harvested JSON-LD, drafts, test fixtures) | `sparqld` |

The `sparql` skill templates in `skills/sparql/queries/*.rq` also work against
sparqld: pass `--endpoint http://127.0.0.1:7737/`.

## Start the endpoint

1. Check whether it is running: `curl -sf http://127.0.0.1:7737/ -o /dev/null`
   (or `sq -e http://127.0.0.1:7737/ graphs`). Only a connection failure means it's stopped.
2. Determine the directory from the user. Ask if unclear; never serve an arbitrary cwd.
3. `sparqld --version`; if missing and cargo is present: `cargo install sparqld`
   (needs rustc >= 1.88; `rustup update` if older).
4. Start in the background, keep logs: `sparqld <dir> > /tmp/sparqld.log 2>&1 &`
5. Retry the check for ~10 s. If it still fails, report the log, do not guess results.

## Python fallback (no Rust)

`scripts/local_sparql.py` loads a folder, file, or URL (`.nq .nt .ttl .trig .jsonld .rdf`, and their `.gz` forms, which sparqld cannot read)
into an in-memory pyoxigraph store (rdflib if pyoxigraph is missing) and either runs one query or
serves a read-only SPARQL endpoint compatible with the `sparql` skill:

```sh
uv run --with pyoxigraph python skills/sparqld/scripts/local_sparql.py data/cchdo -f q.rq
uv run --with pyoxigraph python skills/sparqld/scripts/local_sparql.py data/cchdo --serve --port 7737 &
```

Limits: everything is held in memory; JSON-LD with a relative/remote non-JSON `@context`
(e.g. sparqld's YAML-LD contexts) may fail to parse. Unlike sparqld, it does not watch for edits.

## Demo: raw GitHub URL -> gunzip -> serve -> query (CCHDO from GeoCODES)

sparqld 0.1.4 **ignores `.gz` files** ("1 file ignored", 0 results) and has no
decompression option, so gunzip into the served folder first.

```sh
URL=https://raw.githubusercontent.com/earthcube/decoder-pi/master/data/cchdo/cchdo_release.nq.gz
mkdir -p /tmp/cchdo
curl -sSfL "$URL" | gunzip > /tmp/cchdo/cchdo_release.nq   # 4.4 MB -> 110 MB, 551,904 quads
sparqld /tmp/cchdo > /tmp/sparqld.log 2>&1 &
uv run python skills/sparql/scripts/sparql_query.py run --query list_types --endpoint http://127.0.0.1:7737/
printf '%s\n' 'PREFIX s: <https://schema.org/> SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { ?d a s:Dataset }' \
  | sq -e http://127.0.0.1:7737/                            # -> 3094
```

The Python fallback reads the `.gz` (local path or URL) directly, no gunzip:

```sh
uv run --with pyoxigraph python skills/sparqld/scripts/local_sparql.py "$URL" \
  -q 'PREFIX s: <https://schema.org/> SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { ?d a s:Dataset }'
```

Note: sparqld renames graphs to `sparqld:<file>#<original graph IRI>` and adds file-catalog
triples (sd:/nfo:), so its triple counts are higher than the raw file's and graph filters need `CONTAINS`.
See `data/cchdo/README.md` for license and citation.

## Query

```sh
# with sq
printf '%s\n' 'SELECT DISTINCT ?t (COUNT(*) AS ?n) WHERE { ?s a ?t } GROUP BY ?t' \
  | sq -e http://127.0.0.1:7737/
# with curl
curl -s http://127.0.0.1:7737/ --data-urlencode 'query@q.rq' \
  -H 'Accept: text/tab-separated-values'
# with the repo's sparql skill runner
uv run python skills/sparql/scripts/sparql_query.py run probe_triples --endpoint http://127.0.0.1:7737/
```

Workflow: inspect types/predicates with small `SELECT DISTINCT` queries, follow
the vocabulary the data actually uses (http vs https schema.org), use `DISTINCT`
(several files may state the same fact), each file is a named graph.

## Response

Answer concisely, separate graph facts from inference, include the final query
in a `sparql` block. Read-only: never send SPARQL Update.
