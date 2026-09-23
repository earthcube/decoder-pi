# Example Pi prompts

Copy-paste these into a session started from this repo. Each prompt names **one**
endpoint so the agent does not have to guess, and it says which PNGs to write
under `runs/`.

```bash
./bin/pi
```

Skills load from `skills/` via `extensions/load-skills.ts`. You can also force
one with `/skill:sparql`, `/skill:catalog-plot`, `/skill:catalog-map`,
`/skill:forecast-inventory`, `/skill:forecast-parquet`, `/skill:surface-inventory`,
`/skill:hydrography-tiles`, or `/skill:geotiff-list`.

## One graph per chain

These catalogs do **not** overlap. Never put two endpoints in the same prompt
or join their results.

| Catalog | SPARQL URL | What it is |
|---|---|---|
| deepoceans | `https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans` | Ocean observation **metadata** (schema.org, DepBelowSurf, cruise tracks) |
| ecoforecast | `https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast` | EFI/NEON **forecast catalog** (STAC, site points, parquet downloads) |
| earthsurface | `https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface` | Land hydrography / climate / geochemistry **metadata** (20° tiles, GeoTIFF URLs) |

SPARQL returns catalog fields (counts, min/max, lat/lon, download URLs). Numeric
CRPS / forecast series come from parquet on **ecoforecast only**, not from RDF
literals and not from deepoceans.

**Deepoceans chain**

```text
sparql  →  table/JSON
            ├─ catalog-plot   (types, providers, variables, depth-hist, depth-ranges)
            └─ catalog-map    (points, boxes, WKT, near)
```

**Ecoforecast chain**

```text
sparql  →  table/JSON
            ├─ forecast-inventory  (themes, models, columns, sites-map)
            ├─ catalog-map         (points, boxes, WKT, near) on this graph only
            └─ forecast-parquet    (list URL → GET one file → series, or one lead)
```

`catalog-plot depth-hist` / `depth-ranges` belong on deepoceans. `forecast-*`
skills belong on ecoforecast. `surface-inventory` / `hydrography-tiles` /
`geotiff-list` belong on earthsurface.

**Earthsurface chain**

```text
sparql  →  table/JSON
            ├─ surface-inventory   (providers, themes, formats, ai-flag)
            ├─ catalog-plot        (types, providers — not depth-hist)
            ├─ catalog-map         (boxes, wkt — not points/near)
            ├─ hydrography-tiles   (grid, lookup, layers)
            └─ geotiff-list        (URL table, no raster download)
```

## What is actually scientific in these graphs

These stores are **discovery catalogs**. They do not hold CTD casts, CHELSA rasters, or EFI forecast files as RDF literals. Live counts that matter:

| Graph | Numeric / spatial you can use | What it is *not* |
|---|---|---|
| deepoceans | `DepBelowSurf` min/max (~4.8k datasets, almost all `urn:doos:obis`); CCHDO lat/lon (~38.6k pairs) and `MULTIPOINT` tracks; claimed `variableMeasured` names | Water-column time series; Argo/BCO-DMO point maps (those providers barely appear in lat/lon) |
| ecoforecast | Parquet **scores** (`crps`, `observation`, `mean`, quantiles), a single lead via `forecast-parquet horizon`, and **forecast summaries**; NEON site coordinates | CRPS in SPARQL; a global “best model” ranking from one file |
| earthsurface | 20° hydrography tile bboxes/WKT; GeoTIFF **URLs** (accumulation, CTI, channel elevation); CHELSA **names + units** | Climate time series; GLORICH chemistry values; plottable 90 m rasters in-session |

Do **not** add skills that would: join the three graphs, histogram `temporalCoverage` (many `None/None` and implausible years), treat hydrography `wet_weight`/`cruiseid` as data, or download 90 m GeoTIFFs by default.

No new skill folder is justified until someone repeatedly needs **forecast obs-vs-mean scatter** or **lat/lon maps filtered by named graph**. Those are small extensions of `forecast-parquet` and `catalog-map`, not new domains.

---

# Deepoceans examples

## 1. Orient (sparql → catalog-plot)

**Prompt**

```text
Use endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

1. Probe the store (sparql probe_triples, limit 5, --show-query).
2. Plot rdf:type counts (catalog-plot types) to runs/ex1-types.png.
3. Plot datasets per provider (catalog-plot providers) to runs/ex1-providers.png.

Report row counts honestly. Do not invent bindings. Do not query ecoforecast.
```

**Skills:** `sparql` → `catalog-plot`  
**Expect:** a few sample triples; a type bar (PropertyValue / Dataset / Place / …);
provider bars (bcodmo, cchdo, emodnet, obis, …).

---

## 2. Depth profile of the catalog (sparql → catalog-plot)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

Chain:
- catalog-plot depth-hist → runs/ex2-depth-hist.png
- sparql run depth_minmax --limit 80 --format json, then catalog-plot
  depth-ranges --from-json of that file → runs/ex2-depth-ranges.png
- catalog-plot variables → runs/ex2-variables.png

Summarize: how many DepBelowSurf series fall in <50 m vs >=4000 m, and what
the top variableMeasured names are. Do not use depth_assay for the ranking.
Stay on this endpoint only.
```

**Skills:** `sparql` + `catalog-plot`  
**Expect:** binned max-depth histogram; min–max strip (depth down); ranked names
such as `depth`, `DepBelowSurf`, `pressure`, `ctd_temperature`.

---

## 3. Where is the ocean data? (sparql → catalog-map)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

1. sparql count_spatial — how many subjects have geometry or spatialCoverage?
2. catalog-map points --limit 3000 → runs/ex3-points.png (keep coastlines).
3. catalog-map boxes --limit 200 → runs/ex3-boxes.png.
4. catalog-map wkt --limit 40 → runs/ex3-wkt.png.

Tell me which figure is lat/lon scatter, which is schema:box, and which is
CCHDO-style MULTIPOINT tracks. Do not use geof:distance or QLever spatialSearch.
```

**Skills:** `sparql` → `catalog-map`  
**Expect:** a large spatial-subject count; a global point map with coastlines;
EMODNet-style boxes; cruise tracks as WKT.

---

## 4. Nearby sites (catalog-map near, client haversine)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

Find catalog points within 800 km of 32 N, 88 W (northern Gulf of Mexico).
Use catalog-map near --lat 32 --lon -88 --km 800 --limit 8000
→ runs/ex4-near.png.

Print a table of the nearest 15 (km, lat, lon, s). Distance must be haversine
in the client, not GeoSPARQL.
```

**Skills:** `catalog-map` (`near`)  
**Expect:** a zoomed map with a radius circle, coastline, and a km table. Empty
is allowed if this slice of the `--limit` sample has no hits — say so.

A Southern Ocean variant (CCHDO tracks): `--lat -62 --lon -58 --km 800`.

---

## 5. JSON hand-off (sparql → plot/map)

Use when you want the agent to **save SPARQL JSON** and reuse it, instead of
hitting the endpoint twice.

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

1. sparql run depth_minmax --limit 50 --format json, save to runs/ex5-depth.json
2. catalog-plot depth-ranges --from-json runs/ex5-depth.json → runs/ex5-ranges.png
3. sparql file skills/catalog-map/queries/latlon.rq --limit 500 --format json
   save to runs/ex5-latlon.json
4. catalog-map points --from-json runs/ex5-latlon.json → runs/ex5-points.png

Show the SPARQL for step 1 (--show-query). Stay on deepoceans.
```

**Skills:** `sparql` → `catalog-plot` / `catalog-map` via `--from-json`

---

## 6. Offline deepoceans fixtures

```text
Do not call any SPARQL endpoint. Ocean-catalog fixtures only:

- catalog-plot depth-hist --from-json skills/catalog-plot/fixtures/depth_hist.json
  → runs/ex6-hist.png
- catalog-plot depth-ranges --from-json skills/catalog-plot/fixtures/depth_minmax.json
  → runs/ex6-ranges.png
- catalog-plot variables --from-json skills/catalog-plot/fixtures/variables.json
  → runs/ex6-variables.png

Report the PNG paths. Do not use forecast fixtures.
```

**Skills:** `catalog-plot`

---

# Ecoforecast examples

## 7. Catalog then sites (forecast-inventory → catalog-map)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

1. forecast-inventory themes → runs/ex7-themes.png
2. forecast-inventory columns  (markdown only)
3. forecast-inventory sites-map --limit 4000 → runs/ex7-sites.png

Explain that variableMeasured names like prediction/crps/mean are file columns
in RDF, not numeric series. Do not download parquet in this prompt.
Do not query deepoceans.
```

**Skills:** `forecast-inventory` (sites-map calls `catalog-map points`)  
**Expect:** theme bars (Aquatics, Phenology, … plus `(no STAC theme)`);
a column table; a North America–heavy site scatter with coastlines.

---

## 8. Nearby NEON sites (catalog-map near)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

Use catalog-map near --lat 39.1 --lon -96.56 --km 400 --limit 4000
→ runs/ex8-near.png
(Konza Prairie / KONZ area).

Print the nearest 15 sites (km, lat, lon, s). Haversine only; no GeoSPARQL.
Stay on ecoforecast.
```

**Skills:** `catalog-map` (`near`)  
**Expect:** a regional map of forecast site coordinates around the central US.

---

## 9. From catalog to CRPS time series (inventory → parquet)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

Chain:
1. forecast-inventory themes → runs/ex9-themes.png
2. forecast-parquet list --contains scores/bundled-parquet --limit 15
3. Pick one URL whose path contains model_id=tg_tbats (or the first scores
   URL if that model is absent). Plot CRPS vs datetime for site TALL:
   forecast-parquet plot --url … --y crps --site TALL → runs/ex9-crps.png
4. Download only that one parquet object. Do not crawl the catalog.

Report the parquet columns, row count, and how many TALL rows were plotted.
Do not query deepoceans.
```

**Skills:** `forecast-inventory` → `forecast-parquet`  
**Expect:** a theme bar; a short URL list of OSN `s3://anonymous@…` prefixes;
a CRPS line chart. SPARQL must not be treated as the source of CRPS numbers.
That line stacks every issue date on its target date. Example 9b keeps one lead.

Chlorophyll summary variant (still ecoforecast): `--contains 'variable=chla' --y mean`
(forecast `bundled-summaries`, not scores).

---

## 9b. One lead at a time (forecast-parquet horizon)

`plot` draws every issue date that lands on a target date as one line. A lead is
`datetime` minus `reference_datetime`, in whole days. `horizon` keeps one lead,
so each target date is one stored CRPS. The score is neon4cast's. This command
does not build a forecast distribution or evaluate the CRPS integral.

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

1. forecast-parquet list --contains 'variable=amblyomma_americanum/model_id=tg_tbats' --limit 5
2. On that scores URL, with no --lead:
   forecast-parquet horizon --url … --site TALL --y crps
   This prints scored-row counts by lead and does not write a PNG.
3. Choose the shortest positive lead whose duplicate_targets is 0 and whose
   scored_rows is at least 5. Then:
   forecast-parquet horizon --url … --site TALL --y crps --lead <N>
   → runs/ex9b-horizon.png

Explain in the reply:
- CRPS is the value stored by neon4cast scoring, not recomputed here.
- The PNG is one model (tg_tbats), one variable (amblyomma_americanum), one
  site (TALL), and one lead. It is not a model ranking.
- Say the lead in days, how many target dates were plotted, the min and max
  CRPS, and any gap larger than the usual step between targets.
- A handful of target dates does not support a seasonal claim.
- If a lead's duplicate_targets is greater than 0, that target was scored
  more than once (often a new pub_datetime). Do not average those rows.

Download one parquet object. Do not query deepoceans or earthsurface.
```

**Skills:** `forecast-parquet` (`horizon`)  
**Expect:** a lead table for TALL, then a short marked CRPS series at one lead.
On the ticks scores file, most leads have only a few target dates, and a few
long leads have two scores for the same target. The chosen lead has
`duplicate_targets` 0.

Offline, the same filter on a synthetic file (no endpoint):

```text
Do not call any SPARQL endpoint.

forecast-parquet horizon --from-parquet skills/forecast-parquet/fixtures/scores_horizon.parquet --site TALL
then forecast-parquet horizon --from-parquet skills/forecast-parquet/fixtures/scores_horizon.parquet --site TALL --lead 7 --y crps
→ runs/ex9b-horizon-offline.png

The fixture is synthetic. Lead 7 at TALL has five target dates and one gap
(three weeks between 2024-06-17 and 2024-07-08). Say that the gap is not
filled in. Lead 14 is a different series and must not appear on this PNG.
```

---

## 10. Offline ecoforecast fixtures

```text
Do not call any SPARQL endpoint. Forecast-catalog fixtures only:

- forecast-inventory themes --from-json skills/forecast-inventory/fixtures/datasets.json
  → runs/ex10-themes.png
- forecast-parquet plot --from-parquet skills/forecast-parquet/fixtures/scores_sample.parquet
  --y crps → runs/ex10-crps.png

Report the PNG paths. Do not use catalog-plot depth fixtures.
```

**Skills:** `forecast-inventory`, `forecast-parquet`

---

# Earthsurface examples

## 11. Orient the land catalog (surface-inventory)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface.

1. surface-inventory providers → runs/ex11-providers.png
2. surface-inventory themes → runs/ex11-themes.png
3. surface-inventory formats → runs/ex11-formats.png
4. surface-inventory ai-flag (table only)

Do not query deepoceans or ecoforecast. Do not download GeoTIFFs.
Do not treat variableMeasured names like wet_weight as real measurements.
```

**Skills:** `surface-inventory`  
**Expect:** provider bars (hydrography90m, aiesd, geochemistry_custom); themes
including hydrography and climate; GeoTIFF-heavy formats; some AI-generated
metadata rows.

---

## 12. Hydrography tile grid (hydrography-tiles + catalog-map boxes)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface.

1. hydrography-tiles grid → runs/ex12-grid.png
2. catalog-map boxes --limit 200 → runs/ex12-boxes.png
3. hydrography-tiles lookup --lat 40 --lon -105
4. hydrography-tiles layers --tile <the tile id from step 3> --limit 400

Stay on earthsurface. Client-side rectangle lookup, not GeoSPARQL.
```

**Skills:** `hydrography-tiles`, `catalog-map`  
**Expect:** a global 20° tile map with `hXXvYY` labels; matching boxes; one tile
id for Colorado; a layer table (accumulation, cti, channel_elv, …).

---

## 13. List rasters for one tile (geotiff-list)

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface.

geotiff-list list --contains h10v04 --limit 15

Print filenames and URLs only. Do not download the TIFFs.
Do not query other graphs.
```

**Skills:** `geotiff-list`

---

## 14. Offline earthsurface fixtures

```text
Do not call any SPARQL endpoint. Earthsurface fixtures only:

- surface-inventory providers --from-json skills/surface-inventory/fixtures/providers.json
  → runs/ex14-providers.png
- hydrography-tiles lookup --from-json skills/hydrography-tiles/fixtures/tile_datasets.json
  --lat 30 --lon -70 → runs/ex14-lookup.png
- geotiff-list list --from-json skills/geotiff-list/fixtures/downloads.json --contains h10v04

Report the PNG paths. Do not use deepoceans or ecoforecast fixtures.
```

**Skills:** `surface-inventory`, `hydrography-tiles`, `geotiff-list`

---

# Scientifically motivated prompts (current skills)

These stay on **one** graph. They use existing CLIs. They ask catalog or parquet questions a domain scientist might actually care about.

## D1. How deep does the ocean catalog claim to sample? (OBIS depth ranges)

`DepBelowSurf` min/max in this graph is almost entirely `urn:doos:obis` (occurrence depth), plus a small BCO-DMO set. It is **not** a CTD profile archive.

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

1. catalog-plot depth-hist → runs/sci-d1-hist.png
2. catalog-plot depth-ranges (limit 80) → runs/sci-d1-ranges.png

Interpret bins as claimed biological/occurrence depth in the catalog
(<50 m mixed layer vs >=4000 m abyss), not as measured profiles.
Do not query other graphs.
```

## D2. GO-SHIP / CCHDO tracks in the Southern Ocean

Nearly all `schema:latitude`/`longitude` triples are CCHDO. A points map of deepoceans is a **hydrographic-cruise map**, not a federated-provider map.

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

1. catalog-map wkt --limit 80 → runs/sci-d2-wkt.png
2. catalog-map near --lat -60 --lon -60 --km 1500 --limit 8000
   → runs/sci-d2-near.png
   (Drake Passage / west Antarctic Peninsula)

Describe this as CCHDO station/track metadata. Do not claim Argo coverage
from these figures.
```

## D3. What is catalogued near Station ALOHA (HOT)?

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans.

catalog-map near --lat 22.75 --lon -158 --km 250 --limit 8000
→ runs/sci-d3-aloha.png

Print the nearest 15 (km, lat, lon, s). Haversine only.
This is metadata proximity to the HOT site, not HOT bottle data.
```

## E1. EFI forecast skill at one NEON site (CRPS)

Scores parquet holds real `crps` / `observation` / `mean`. One model, one site is a valid verification slice — not a leaderboard. `plot` stacks every lead on the target date. For one lead, use example 9b (`horizon`).

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

1. forecast-parquet list --contains scores/bundled-parquet --limit 15
2. Plot CRPS vs time for site TALL from one scores URL (prefer model_id=tg_tbats
   if present) → runs/sci-e1-crps.png
3. Same file, --y observation → runs/sci-e1-obs.png
   and --y mean → runs/sci-e1-mean.png

State that this is one model × one site. Do not rank models. Do not query
deepoceans or earthsurface. Download one parquet only.
```

## E2. Aquatic chlorophyll forecast (summaries, not scores)

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

forecast-parquet list --contains 'forecasts/bundled-summaries' --contains chla
then plot --y mean for one chlorophyll summary parquet
→ runs/sci-e2-chla.png

This is a forecast mean of chlorophyll-a, not an in-situ time series.
```

## S1. Hydrography layers for a Rocky Mountain catchment

90 m flow-accumulation / CTI / channel elevation are standard inputs for
catchment work. The graph gives the **tile index and URLs**, not the rasters.

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface.

1. hydrography-tiles lookup --lat 40.01 --lon -105.3
   (Front Range / Boulder Creek area)
2. hydrography-tiles layers --tile <id from step 1>
3. geotiff-list list --contains <that tile> --limit 20

Name the tile and the layer stems (accumulation, cti, channel_elv, …).
Do not download GeoTIFFs. Do not query the other graphs.
```

## S2. CHELSA predictors present in the catalog (SDM metadata)

CHELSA `variableMeasured` rows have climate **names and units** (K or °C, kg m⁻²)
but no min/max values. Useful as a predictor inventory for species-distribution
work, not as a climate plot.

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/earthsurface.

Use sparql (ad-hoc, --show-query) to list distinct variableMeasured names and
unitText containing temperature, precipitation, humidity, or wind.
Then surface-inventory themes → runs/sci-s2-themes.png

Do not invent numeric climatologies. Do not download CHELSA rasters.
```

---

## Notes for the agent (and for you)

- Run CLIs from the **decoder-pi repo root** with `uv run python skills/…`.
- Write figures under `runs/` (`runs/` is gitignored).
- Prefer canned skill modes over ad-hoc matplotlib or invented SPARQL.
- Portable SPARQL only: no `geof:distance`, no QLever `spatialSearch:`.
- One parquet object per plot; 80 MiB download cap.
- If a step returns 0 rows, say so and skip the PNG rather than fabricating data.
- **Never mix deepoceans, ecoforecast, and earthsurface in one chain.** They are unrelated catalogs.
- Scoring one ecoforecast scores file, or one deepoceans CSV distribution, for AI readiness is a separate prompt: [`AIDRIN_EXAMPLE.md`](AIDRIN_EXAMPLE.md).
