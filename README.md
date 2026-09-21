# decoder-pi

A lightweight [Pi](https://pi.dev) harness: skills and extensions live in this
directory and are loaded at launch. They are **not** installed into global Pi
settings (`~/.pi/agent/settings.json`) or a project `.pi/` config.

Pi 0.85.1+ is required (`pi` on `PATH`). Your existing provider auth, models,
and global packages stay in global Pi settings. This repo only adds local skills.

## Launch

From this repo (loads every `SKILL.md` under `skills/`):

```bash
./bin/pi
```

That is:

```bash
pi --no-skills -e /path/to/decoder-pi/extensions/load-skills.ts
```

`--no-skills` turns off discovery of `~/.pi/agent/skills/`, `.pi/skills/`, and
settings skill paths. The extension then contributes this repo's `skills/`
directory (resolved from the extension file, so cwd does not matter).

Without the extension (same skill set):

```bash
pi --no-skills --skill ./skills
```

One skill only:

```bash
pi --no-skills --skill ./skills/sparql
```

Keep your global skills as well (omit `--no-skills`):

```bash
pi --skill ./skills
```

From any directory:

```bash
pi --no-skills -e /home/fils/src/Projects/earthcube/decoder-pi/extensions/load-skills.ts
```

Do **not** run `pi install` on this repo. Extra args (`--print`, `--model`, an
initial prompt) pass through `./bin/pi`.

Inside a session: `/skill:sparql`, `/skill:catalog-plot`, `/skill:catalog-map`,
`/skill:forecast-inventory`, `/skill:forecast-parquet`, `/skill:surface-inventory`,
`/skill:hydrography-tiles`, `/skill:geotiff-list`.

## Layout

```text
decoder-pi/
├── bin/pi                         # launcher
├── extensions/load-skills.ts      # resources_discover → skills/
├── skills/
│   ├── sparql/                    # SPARQL 1.1 CLI + templates
│   ├── catalog-plot/              # bars, depth hist/ranges
│   ├── catalog-map/               # lat/lon, box, WKT, coastlines, near
│   ├── forecast-inventory/        # ecoforecast catalog
│   ├── forecast-parquet/          # parquet CRPS / mean, or one lead
│   ├── surface-inventory/         # earthsurface catalog
│   ├── hydrography-tiles/         # 20° hydrography tile index
│   └── geotiff-list/              # raster URL table (no download)
├── pyproject.toml                 # SPARQLWrapper + matplotlib + pyarrow
└── AGENTS.md
```

Add another skill as `skills/<name>/SKILL.md`. `./bin/pi` picks it up with no
command change.

## SPARQL skill

Adapted from DOOS `doos-sparql`. Curated schema.org / GeoSPARQL templates plus
ad-hoc SPARQL 1.1. Always requires an explicit `--endpoint`.

```bash
uv sync   # once; SPARQLWrapper

uv run python skills/sparql/scripts/sparql_query.py list

uv run python skills/sparql/scripts/sparql_query.py run \
  --endpoint http://localhost:7878/query \
  --query probe_triples \
  --show-query
```

See `skills/sparql/SKILL.md` for the cookbook and remaining templates.

## Example Pi prompts

Copy-paste session prompts that chain SPARQL → plot/map/parquet are in
[`EXAMPLES.md`](EXAMPLES.md).

## Plot / map / inventory skills

These consume SPARQL JSON (or `--endpoint`, which shells out to the SPARQL CLI).
They plot **catalog metadata**, not observation time series.

```bash
EP=https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans
EF=https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast

uv run python skills/catalog-plot/scripts/plot.py depth-hist --endpoint $EP
uv run python skills/catalog-plot/scripts/plot.py depth-ranges --endpoint $EP
uv run python skills/catalog-map/scripts/map.py points --endpoint $EP --limit 2000
uv run python skills/catalog-map/scripts/map.py near --endpoint $EP --lat -62 --lon -58 --km 800
uv run python skills/forecast-inventory/scripts/inventory.py themes --endpoint $EF
uv run python skills/forecast-parquet/scripts/parquet_plot.py plot \
  --endpoint $EF --contains 'scores/bundled-parquet' --y crps --site TALL
uv run python skills/forecast-parquet/scripts/parquet_plot.py horizon \
  --from-parquet skills/forecast-parquet/fixtures/scores_horizon.parquet \
  --site TALL --lead 7 --y crps
```

Offline fixtures:

```bash
uv run python skills/catalog-plot/scripts/plot.py depth-hist \
  --from-json skills/catalog-plot/fixtures/depth_hist.json -o /tmp/depth-hist.png
```
