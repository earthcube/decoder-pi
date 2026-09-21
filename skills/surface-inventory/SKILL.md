---
name: surface-inventory
description: >
  Earthsurface catalog analytics: provider bars, theme bars (hydrography,
  CHELSA climate, land cover, geochemistry), encodingFormat bars, list of
  AI-generated metadata datasets. Use for the earthsurface graph only.
  Triggers: earthsurface, hydrography90m, CHELSA, land cover, GLHYMPS,
  /skill:surface-inventory. Not for: deepoceans, ecoforecast, DepBelowSurf,
  CRPS, downloading GeoTIFF tiles.
license: Apache-2.0
compatibility: python3, uv, matplotlib (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# Surface inventory

Catalog-only skill for
`https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface`.

Do **not** mix this graph with deepoceans or ecoforecast. Hydrography
`variableMeasured` names such as `wet_weight` / `cruiseid` are metadata noise —
do not plot them as measurements. CHELSA variables have names and units but
**no min/max** in RDF.

## CLI

```bash
ES=https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface

uv run python skills/surface-inventory/scripts/inventory.py providers --endpoint $ES
uv run python skills/surface-inventory/scripts/inventory.py themes --endpoint $ES
uv run python skills/surface-inventory/scripts/inventory.py formats --endpoint $ES
uv run python skills/surface-inventory/scripts/inventory.py ai-flag --endpoint $ES
```

| Mode | Output |
|---|---|
| `providers` | hydrography90m / aiesd / geochemistry_custom |
| `themes` | hydrography, climate, land cover, GPP, geochemistry, … |
| `formats` | GeoTIFF / GeoPackage / NetCDF / … |
| `ai-flag` | table of `AI-generated metadata` datasets (no PNG) |

For maps of 20° tiles use `hydrography-tiles`. For GeoTIFF URLs use `geotiff-list`.
For generic type bars, `catalog-plot types` on this endpoint is fine.
