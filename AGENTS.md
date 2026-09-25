# decoder-pi

This directory is a Pi coding-agent harness. Skills live in `skills/` and are
loaded at launch by `extensions/load-skills.ts` (via `./bin/pi`), not from
`~/.pi/agent` or a project `.pi/` config.

Skills:

- `skills/sparql` — SPARQL 1.1 CLI + templates. Always pass `--endpoint`.
- `skills/catalog-plot` — bars / depth hist / min–max strips from SPARQL JSON.
- `skills/catalog-map` — lat/lon, schema:box, WKT, coastlines, haversine `near`.
- `skills/forecast-inventory` — ecoforecast catalog (themes, models, columns).
- `skills/forecast-parquet` — SPARQL finds parquet URL, HTTP GET, plot CRPS/mean or one lead (`horizon`).
- `skills/surface-inventory` — earthsurface catalog (providers, themes, formats).
- `skills/hydrography-tiles` — 20° hydrography.org tile grid / lookup / layers.
- `skills/geotiff-list` — list GeoTIFF URLs; does not download rasters.
- `skills/setgo` — metadata assessment via the `setgo` command on `PATH`. ORCID name search is not that command: from this repo root run `uv run --no-project --with-editable /home/fils/src/git/setgo python skills/setgo/scripts/lookup_orcid.py`.

The graphs are catalog metadata. Do not treat `prediction` / `crps` as numeric
SPARQL values; plot those from parquet. Distance is client-side haversine, not
QLever GeoSPARQL. Hydrography `wet_weight`/`cruiseid` names on earthsurface are
noise. Run CLIs from this repo root with `uv run python skills/<skill>/scripts/…`.

Chained session prompts: `EXAMPLES.md`. Never mix deepoceans, ecoforecast, and
earthsurface in one chain.
