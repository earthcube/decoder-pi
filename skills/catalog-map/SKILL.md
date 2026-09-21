---
name: catalog-map
description: >
  Map schema.org / GeoSPARQL catalog geography from SPARQL JSON: latitude/
  longitude scatter, schema:box, asWKT, optional 110m coastlines, and
  client-side haversine "near" filter. Use when the user wants a map of
  datasets or sites, or points within N km of a lat/lon. Triggers: map,
  lat/lon, bounding box, WKT, coastline, nearby, haversine, /skill:catalog-map.
  Not for: QLever geof:distance / spatialSearch, depth histograms, parquet.
license: Apache-2.0
compatibility: python3, uv, matplotlib (decoder-pi pyproject.toml)
metadata:
  project: decoder-pi
  version: "1.0"
---

# Catalog map

Plot **spatial fields already in the graph**. Equirectangular matplotlib PNG
with bundled Natural Earth 110m coastlines (public domain). Distance is
**haversine in the client**, not GeoSPARQL — works on Oxigraph and QLever.

## Agent workflow

1. Confirm `--endpoint` or SPARQL JSON.
2. Choose `points`, `boxes`, `wkt`, or `near` (`--lat --lon --km`).
3. Run from the **decoder-pi repo root**.
4. Report PNG path and how many geometries plotted vs skipped.

`schema:box` has two live formats; the CLI parses both:

- space: `minLat minLon maxLat maxLon` (EMODNet / deepoceans)
- comma: `lat,lon lat,lon` (neon4cast / ecoforecast)

WKT is treated as lon/lat (GeoSPARQL). Huge geometries are truncated.

## CLI

```bash
uv run python skills/catalog-map/scripts/map.py points \
  --endpoint URL --limit 4000 -o runs/points.png

uv run python skills/catalog-map/scripts/map.py boxes \
  --endpoint URL --limit 300 -o runs/boxes.png

uv run python skills/catalog-map/scripts/map.py wkt \
  --endpoint URL --limit 80 -o runs/wkt.png

uv run python skills/catalog-map/scripts/map.py points \
  --from-json /tmp/latlon.json -o runs/points.png

uv run python skills/catalog-map/scripts/map.py near \
  --from-json /tmp/latlon.json --lat 32 --lon -88 --km 400 -o runs/near.png

# skip coastlines
uv run python skills/catalog-map/scripts/map.py points --no-coastlines --endpoint URL
```

| Mode | Query | Geometry |
|---|---|---|
| `points` | `queries/latlon.rq` | scatter + coastlines |
| `boxes` | `queries/boxes.rq` | rectangles |
| `wkt` | `queries/wkt.rq` | MULTIPOINT scatter, POLYGON outline |
| `near` | same lat/lon JSON | haversine radius around `--lat --lon --km` |

`--coastlines` is on by default; `--no-coastlines` turns it off.

## Do not

- Use QLever `spatialSearch:` or `geof:distance` (not portable to Oxigraph)
- Fetch remote coastline/raster tiles
- Treat empty SPARQL as an empty ocean of zeros
- Plot forecast parquet series (use `forecast-parquet`)
