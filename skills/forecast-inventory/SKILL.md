---
name: forecast-inventory
description: >
  Ecoforecast (neon4cast / vera4cast) catalog analytics: STAC theme bars, model
  id bars, variableMeasured column inventory, site lat/lon map. Use when the
  user asks about EFI/NEON forecasts in the ecoforecast graph. Triggers:
  neon4cast, vera4cast, ecoforecast, forecast catalog, CRPS columns, /skill:forecast-inventory.
  Not for: downloading parquet (use forecast-parquet), inventing CRPS from RDF, ocean depth.
license: Apache-2.0
compatibility: python3, uv, matplotlib (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# Forecast inventory

The ecoforecast graph is a **STAC/schema.org catalog**. `variableMeasured`
names such as `prediction`, `mean`, `quantile97.5`, and `crps` are **file
columns**, not numeric series in RDF. This skill inventories that catalog.

Default endpoint (ask first):
`https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast`

## Agent workflow

1. Confirm the ecoforecast endpoint (or JSON).
2. Pick `themes`, `models`, `columns`, or `sites-map`.
3. For depth/ocean plots, switch to `catalog-plot` on deepoceans instead.
4. Say clearly when a result is a column name rather than a value.

## CLI

```bash
EP=https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast

uv run python skills/forecast-inventory/scripts/inventory.py themes \
  --endpoint $EP -o runs/themes.png

uv run python skills/forecast-inventory/scripts/inventory.py models \
  --endpoint $EP -o runs/models.png

uv run python skills/forecast-inventory/scripts/inventory.py columns \
  --endpoint $EP

uv run python skills/forecast-inventory/scripts/inventory.py sites-map \
  --endpoint $EP --limit 4000 -o runs/sites.png
```

| Mode | Output |
|---|---|
| `themes` | bars from STAC URL `/forecasts/<theme>/<variable>/models/<model>` (datasets without that path are `(no STAC theme)`) |
| `models` | bars of model ids (`schema:name` / URL) |
| `columns` | markdown table of variableMeasured names (no PNG) |
| `sites-map` | delegates to `catalog-map points` |

For CRPS / mean time series from the parquet `contentUrl`, use **`forecast-parquet`**. For one lead (one score per target date), use `forecast-parquet horizon`.

## Do not

- Treat `crps` / `prediction` as SPARQL numbers
- Mix this skill with DepBelowSurf charts
