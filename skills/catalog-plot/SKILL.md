---
name: catalog-plot
description: >
  Plot catalog analytics from SPARQL JSON: type/provider/variable bars,
  DepBelowSurf depth histograms and min–max range strips, markdown summaries.
  Use when the user wants a chart or inventory of a schema.org graph (not a map).
  Triggers: plot, bar chart, histogram, depth range, variable ranking, list_types
  chart, catalog analytics, /skill:catalog-plot. Not for: maps, lat/lon, WKT,
  forecast parquet/time series, SHACL.
license: Apache-2.0
compatibility: python3, uv, matplotlib, SPARQLWrapper (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# Catalog plot

Turn **SPARQL result tables** into PNG bar/histogram/range charts. Query via
`skills/sparql` (or `--endpoint` on this CLI). Do not invent rows.

This is **metadata analytics**. Depth charts need numeric `DepBelowSurf`
min/max (present on deepoceans, absent on ecoforecast).

## Agent workflow

1. Confirm `--endpoint` or a JSON file from `sparql_query.py --format json`.
2. Pick a mode below. Prefer canned modes over ad-hoc matplotlib.
3. Run from the **decoder-pi repo root**.
4. Report the PNG path and the printed counts. If 0 rows, say so; do not draw fake data.

Default live graphs (only if the user agrees):

- Deepoceans: `https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans`
- Ecoforecast: `https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast`

## CLI

```bash
uv run python skills/catalog-plot/scripts/plot.py <mode> \
  --endpoint URL \
  -o runs/out.png

# or from saved SPARQL JSON
uv run python skills/catalog-plot/scripts/plot.py depth-ranges \
  --from-json /tmp/depth.json -o runs/ranges.png
```

| Mode | Source | Figure |
|---|---|---|
| `types` | sparql `list_types` | rdf:type bars |
| `providers` | `queries/datasets_per_provider.rq` | datasets per slug |
| `variables` | `queries/top_variables.rq` (COUNT desc) | top variableMeasured names |
| `depth-hist` | `queries/depth_hist.rq` | DepBelowSurf maxValue bins |
| `depth-ranges` | sparql `depth_minmax` | min–max strip, depth down |
| `summary` | mix | markdown tables, no PNG |

Do **not** use sparql `depth_assay` for rankings; it sorts by name, not count.

`--limit` applies to fetch modes that support `{{LIMIT}}`. `-o` defaults to
`runs/<mode>-<utc>.png`.

## Do not

- Invent counts or depth values
- Plot ecoforecast `prediction` / `crps` as numbers (they are column names)
- Draw maps (use `catalog-map`)
- Commit large PNGs unless the user asks
