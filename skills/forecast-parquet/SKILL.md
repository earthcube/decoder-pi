---
name: forecast-parquet
description: >
  Download EFI/neon4cast parquet DataDownloads found via SPARQL and plot time
  series (CRPS, mean, observation). Use when the user wants forecast skill or
  predicted values over time, not just catalog bars. Triggers: parquet, CRPS,
  scores, bundled-parquet, OSN, /skill:forecast-parquet, plot forecast.
  Not for: inventing SPARQL numbers, QLever geof:distance, ocean depth charts.
license: Apache-2.0
compatibility: python3, uv, matplotlib, pyarrow (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# Forecast parquet

RDF stores **URLs**, not CRPS values. This skill: portable SPARQL 1.1 for
`schema:DataDownload` + `application/x-parquet` → HTTP GET of one object →
matplotlib series.

Works against any SPARQL 1.1 store that has those triples (Oxigraph or QLever).
Does **not** use `geof:distance` or QLever `spatialSearch:`.

EFI URLs look like:

```text
s3://anonymous@bio230014-bucket01/challenges/scores/bundled-parquet/project_id=neon4cast/duration=P1W/variable=…/model_id=…?endpoint_override=sdsc.osn.xsede.org
```

The CLI lists the prefix, downloads the smallest `.parquet` under it (typically
`data_0.parquet`), and plots `datetime` vs `crps` (or `--y mean`).

## Agent workflow

1. Confirm the ecoforecast `--endpoint` (or a parquet `--url` / local file).
2. `list` first; then `plot --contains model_id=…` (or `--variable` via URL substring).
3. One model/variable per plot. Do not crawl all parquet prefixes.
4. Report PNG path, column used, row count. If the file has no `datetime`/`crps`, say so.

Cap: refuse objects larger than 80 MiB.

## CLI

```bash
EF=https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast

uv run python skills/forecast-parquet/scripts/parquet_plot.py list \
  --endpoint $EF --contains scores/bundled-parquet --limit 20

uv run python skills/forecast-parquet/scripts/parquet_plot.py plot \
  --endpoint $EF --contains 'variable=chla/model_id=cb_prophet' --y mean

uv run python skills/forecast-parquet/scripts/parquet_plot.py plot \
  --url 's3://anonymous@bio230014-bucket01/challenges/scores/bundled-parquet/project_id=neon4cast/duration=P1W/variable=amblyomma_americanum/model_id=tg_tbats?endpoint_override=sdsc.osn.xsede.org' \
  --y crps --site TALL -o runs/crps.png

# Offline
uv run python skills/forecast-parquet/scripts/parquet_plot.py plot \
  --from-parquet skills/forecast-parquet/fixtures/scores_sample.parquet --y crps
```

| Mode | Network | Output |
|---|---|---|
| `list` | SPARQL | markdown URL table |
| `plot` | SPARQL optional + HTTP GET of one parquet | PNG series |

Default `--y` order: `crps`, `mean`, `median`, `observation`, `prediction`.

## Do not

- Treat `variableMeasured` names as numeric SPARQL results
- Download every parquet in the catalog
- Use QLever-only spatial functions
