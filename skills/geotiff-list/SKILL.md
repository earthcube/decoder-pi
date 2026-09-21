---
name: geotiff-list
description: >
  List GeoTIFF / GeoPackage / COG DataDownload URLs from the earthsurface
  graph. Does not download rasters. Use when the user wants tile filenames,
  layer URLs, or HTTP sizes. Triggers: GeoTIFF, GPKG, COG, IGB download,
  /skill:geotiff-list. Not for: plotting rasters, deepoceans, ecoforecast parquet.
license: Apache-2.0
compatibility: python3, uv (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# GeoTIFF list

SPARQL → table of raster download URLs. **v1 does not fetch 90 m tiles**
(they are large). Optional `--head` issues HTTP HEAD for `Content-Length`.

```bash
ES=https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface

uv run python skills/geotiff-list/scripts/list_tifs.py list \
  --endpoint $ES --contains h10v04 --limit 20

uv run python skills/geotiff-list/scripts/list_tifs.py list \
  --endpoint $ES --contains accumulation --limit 10 --head
```

Stay on earthsurface. Do not crawl all ~5k TIFFs.
