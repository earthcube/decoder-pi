---
name: hydrography-tiles
description: >
  Index IGB hydrography.org 90 m / 20° tiles in the earthsurface graph: draw
  the tile grid, look up which tile contains a lat/lon (client-side), list
  GeoTIFF layer stems from contentUrl. Triggers: hydrography90m, h10v04,
  20 degree tile, stream accumulation, CTI, /skill:hydrography-tiles.
  Not for: deepoceans, ecoforecast, GeoSPARQL distance, downloading full tiles.
license: Apache-2.0
compatibility: python3, uv, matplotlib (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# Hydrography tiles

Earthsurface-only. Dataset names look like:

```text
hydrography.org dataset for bounding box (40 -80 20 -60) {tile h10v04}
```

Lookup is a rectangle test on that bbox, not `geof:distance`.

## CLI

```bash
ES=https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface

uv run python skills/hydrography-tiles/scripts/tiles.py grid --endpoint $ES \
  -o runs/hydro-grid.png

uv run python skills/hydrography-tiles/scripts/tiles.py lookup \
  --endpoint $ES --lat 40 --lon -105

uv run python skills/hydrography-tiles/scripts/tiles.py layers \
  --endpoint $ES --tile h10v04 --limit 400
```

| Mode | Output |
|---|---|
| `grid` | map of 20° footprints + `hXXvYY` labels, coastlines on |
| `lookup` | which tile contains `--lat --lon`, highlight on map |
| `layers` | table of GeoTIFF stems (`accumulation`, `cti`, `channel_elv_…`) |

Do not download the `.tif` files here (`geotiff-list` prints URLs only).
