---
name: forecast-parquet
description: >
  Download EFI/neon4cast parquet DataDownloads found via SPARQL and plot time
  series (CRPS, mean, observation) or one forecast lead. Use when the user
  wants forecast skill or predicted values over time, not just catalog bars.
  Triggers: parquet, CRPS, scores, horizon, lead time, one-horizon,
  bundled-parquet, OSN, /skill:forecast-parquet, plot forecast.
  Not for: inventing SPARQL numbers, recomputing CRPS, QLever geof:distance,
  ocean depth charts.
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

`horizon` is the fixed-lead view. Lead is the whole-day difference
`datetime` (target) minus `reference_datetime` (issue time). Omit `--lead`
to print scored-row counts and write nothing. With `--lead N`, each target
date is one stored score. A gap longer than 1.5 times the median step between
target dates is not connected. A target date with two scores (neon4cast
republishes the same issue under a new `pub_datetime`) is reported and not
averaged.

`plot` still draws every lead that shares a target date. When that happens it
prints a notice pointing at `horizon`.

## Agent workflow

1. Confirm the ecoforecast `--endpoint` (or a parquet `--url` / local file).
2. `list` first; then one scores URL (`--contains model_id=…`, or `--variable` via URL substring).
3. One model/variable per plot. Do not crawl all parquet prefixes.
4. For skill over time, use `horizon --site …` with no `--lead`, then rerun
   with one whole-day `--lead` whose `duplicate_targets` is 0.
5. Report PNG path, column, lead in days, target-date count, and gaps.
   Say that CRPS is the stored neon4cast score. If the file has no
   `datetime`/`reference_datetime`, say so.

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

# Fixed lead. The first call only prints the lead table.
uv run python skills/forecast-parquet/scripts/parquet_plot.py horizon \
  --from-parquet skills/forecast-parquet/fixtures/scores_horizon.parquet \
  --site TALL --y crps

uv run python skills/forecast-parquet/scripts/parquet_plot.py horizon \
  --from-parquet skills/forecast-parquet/fixtures/scores_horizon.parquet \
  --site TALL --lead 7 --y crps -o runs/horizon.png
```

| Mode | Network | Output |
|---|---|---|
| `list` | SPARQL | markdown URL table |
| `plot` | SPARQL optional + HTTP GET of one parquet | PNG of every lead on the target date |
| `horizon` | SPARQL optional + HTTP GET of one parquet | Lead table, or one PNG at `--lead` days |

`plot` default `--y` order: `crps`, `mean`, `median`, `observation`, `prediction`.
`horizon` defaults to `crps` and does not fall through to another column.

`scores_sample.parquet` has no `reference_datetime` (the mixed-lead `plot` fixture).
`scores_horizon.parquet` is synthetic: site TALL at leads 7 and 14 days, one
3-week gap at lead 7, one 12-hour lead, and site KONZ at lead 7.

## Do not

- Treat `variableMeasured` names as numeric SPARQL results
- Download every parquet in the catalog
- Use QLever-only spatial functions
- Recompute CRPS, or average two scores that share a target date and a lead
- Describe a `plot` line as a one-horizon series when the notice says several leads were drawn
