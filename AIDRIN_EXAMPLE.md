# AIDRIN example: score one forecast file

Yes. This harness can evaluate the AI readiness of **one local table**, and the
table it can both find and score is an EFI/neon4cast parquet.

The Pi skills discover the file. The AIDRIN MCP server scores it. SPARQL
catalogs, maps, and GeoTIFF URL lists stay on their own skills. AIDRIN reads a
file on disk (CSV, Excel, JSON, NumPy `.npz`, HDF5, Parquet).

Docs for the tool: [AIDRIN](https://aidrin.readthedocs.io/en/latest/index.html)
(DOI [10.5281/zenodo.21798062](https://doi.org/10.5281/zenodo.21798062)). The
MCP workflow is
[AIDRIN Skill](https://aidrin.readthedocs.io/en/latest/aidrin_skill.html).
Numbers below were read from AIDRIN **2026.8.2** through the `aidrin` MCP
server in this repo (`uv run --group aidrin aidrin-mcp`).

## How the two sides meet

| Step | Who | What you get |
|---|---|---|
| Find a download URL | `forecast-parquet list` on the ecoforecast endpoint | OSN `s3://anonymous@…` prefixes. RDF holds the URL, not the CRPS values. |
| Fetch one object | `forecast-parquet plot` or `horizon` | One parquet under `/tmp/decoder-pi-<object key, slashes turned into underscores>`, capped at 80 MiB. |
| Keep one series | A short PyArrow filter (below) | One site, one whole-day lead, one row per target date. |
| Score that file | AIDRIN MCP tools | JSON for quality, structure, and (only if you name the columns) fairness or privacy. |

`./bin/pi` starts in the repo root, so `.mcp.json` launches the server as the
same user. Pass an **absolute path**. A URL, an `s3://` string, or a path that
exists only on another machine is invisible to the server. No Globus Compute
profile is configured here (`list_remote_profiles` is empty); omit `endpoint`
and `profile`.

`list_metrics` on this install reports `mlflow_enabled: false`. Skip
`start_assessment` / `end_assessment`.

The agentic tools (`agentic_build_index`, `agentic_run`) are a different AIDRIN
mode: a YAML config, domain PDFs, an API key, and generated Python. This
example uses the metric tools only.

## Which AIDRIN dimensions apply

AIDRIN groups metrics into six dimensions. Five are on the MCP server, under
the CLI names (`completeness`, `temporal-completeness`, …). Pass those dash
names as `metric`. Pass column lists as comma-separated strings on the
snake_case tool fields (`required_columns`, `duplicate_columns`,
`timestamp_column`). `list_metrics` prints the same fields with dashes
(`timestamp-column`); the tool call uses underscores.

| Dimension | On this parquet | MCP category |
|---|---|---|
| Data quality | Completeness, duplicate rows, outliers, weekly gaps in the target dates | `data-quality` |
| Data structure | Constant identity columns, correlation, skew, kurtosis of the score columns | `data-structure` |
| Impact on AI | Only after you name a real target column. `crps` is a stored score. | `impact-of-data-on-AI` |
| Fairness and bias | Only after you name a label and a sensitive column. A NEON `site_id` is a site code. | `fairness-and-bias` |
| Data governance | Only after you name quasi-identifiers. There is no HIPAA field in these scores. | `data-governance` |
| Understandability / FAIR | DCAT or DataCite JSON in the AIDRIN web UI. This harness queries schema.org catalogs. | not on MCP |

`surface-inventory ai-flag` lists earthsurface datasets whose metadata is
marked AI-generated. It belongs to that catalog's inventory, on its own
endpoint.

## Score the slice you would plot

A scores file stacks sites and leads. AIDRIN then describes that mixture.

On `skills/forecast-parquet/fixtures/scores_horizon.parquet` (12 rows; synthetic):

- Weekly temporal completeness on `datetime` is **100%** (8 of 8 weeks from
  2024-06-03 through 2024-07-22). The lead-14 rows occupy 2024-06-24 and
  2024-07-01, which are the weeks the TALL lead-7 series skips.
- `duplicity` (identical rows) is **0**. `duplicity-by-features` on
  `datetime,site_id` is **2 groups** (16.7%): TALL on 2024-06-03 (lead 0.5 and
  lead 7) and TALL on 2024-06-17 (lead 7 and lead 14).
- The outlier rate on `horizon` is **0.33**, because the other leads sit
  outside the interquartile range of the mixed column.

Filter to site TALL and lead 7 (6 rows) and the same tools say something else:
temporal completeness **75%** (6 of 8 weeks), `duplicity-by-features` **0**,
`horizon` outlier rate **0**. The missing weeks are the three-week gap already
reported by `forecast-parquet horizon` (2024-06-17 to 2024-07-08).

Use the same unit as example 9b in `EXAMPLES.md`: one model, one variable, one
site, one lead, and `duplicate_targets` 0. On a live neon4cast file the lead is
`datetime` minus `reference_datetime` in whole days. This fixture also has a
numeric `horizon` column; a downloaded scores object often does not. The same
issue and target can appear twice under a new `pub_datetime`. When
`duplicate_targets` is greater than 0, stop and say so. Do not average those
rows, and do not hand the doubled rows to AIDRIN as one series.

`scores_sample.parquet` has no `reference_datetime`. It cannot be filtered to
a lead. Use `scores_horizon.parquet` for this example.

## Setup

```bash
uv sync --group aidrin
./bin/pi
```

The offline prompt needs no endpoint. The live prompt uses ecoforecast only.

---

## A. Offline: synthetic TALL lead 7

**Prompt**

```text
Do not call a SPARQL endpoint. Do not download parquet. Do not query
deepoceans or earthsurface.

Score the synthetic forecast file
skills/forecast-parquet/fixtures/scores_horizon.parquet
with the AIDRIN MCP server. The file is one model (tg_tbats), one variable
(amblyomma_americanum), two sites, and three leads. AIDRIN must see one series.

1. list_metrics. If mlflow_enabled is false, do not call start_assessment.
2. summarize_dataset on the fixture (file_type parquet). Absolute path.
3. Write a slice with PyArrow to /tmp/decoder-pi-aidrin-tall-lead7.parquet:
   site_id == TALL and horizon == 7. This fixture stores the lead in `horizon`.
   Keep every column. Do not fill the null score row.
4. On that slice only, call:
   - run_data_quality_check
   - run_aidrin_metric row-level-completeness
     required_columns=datetime,site_id,crps,mean,observation
   - run_aidrin_metric duplicity-by-features
     duplicate_columns=datetime,site_id
   - run_aidrin_metric temporal-completeness
     timestamp_column=datetime frequency=W
   - run_aidrin_metric constant-feature-count
   - run_aidrin_metric max-pairwise-correlation
   - run_aidrin_metric skewness
   - run_aidrin_metric kurtosis
5. For contrast, run temporal-completeness (datetime, W) and
   duplicity-by-features (datetime,site_id) once on the unfiltered fixture.
   Say what those two calls hide.

Write runs/aidrin-tall-lead7.md. Include the slice path, row count, and the
JSON scores. Then say, in prose:

- CRPS is the stored neon4cast column. These commands do not recompute it.
- The 2024-07-22 row has null observation, crps, and mean. That is the
  incomplete row.
- Weekly temporal completeness on the slice counts gaps between target dates.
  Lead 7 means the forecast was issued 7 days before the target. The frequency
  argument is the spacing of those target dates (W).
- family, model_id, variable, site_id, and horizon are constant because the
  slice is one identity. That is expected.
- crps and mean correlate at 1 because this fixture set mean = crps + 1.
  Say that before calling them redundant features.
- Leave the ready-or-not judgment to the reader.

Do not run class-imbalance, feature-relevance, k-anonymity, or
hipaa-compliance. Do not call the agentic tools. Omit endpoint and profile.
```

**Tools:** `forecast-parquet` fixture on disk, then AIDRIN MCP
(`list_metrics`, `summarize_dataset`, `run_data_quality_check`,
`run_aidrin_metric`).

**Expect (AIDRIN 2026.8.2, this fixture):**

Unfiltered file, 12×10. `summarize_dataset` lists ten columns.
`reference_datetime` and `datetime` appear in `columns` and not in the
numeric or categorical stat blocks. `site_id` has TALL (10) and KONZ (2).
`family`, `model_id`, and `variable` each have one value. `observation`,
`crps`, and `mean` each have one missing value. Non-null `observation` is 20
everywhere.

| Check | Unfiltered fixture | TALL, horizon 7 (6 rows) |
|---|---|---|
| Overall completeness | 0.975 | 0.95 |
| `crps` / `mean` / `observation` completeness | 0.9167 | 0.8333 (5 of 6 rows) |
| Row-level completeness of those five columns | 91.7% (11/12) | 83.3% (5/6) |
| Identical-row duplicity | 0 | 0 |
| `duplicity-by-features` on `datetime,site_id` | 2 groups, 16.7% | 0 |
| Outlier rate on `horizon` | 0.333 | 0 |
| Outlier rate on `crps` and on `mean` | 0.0909 | 0.2 (the 40 and 41 on 2024-07-08) |
| Temporal completeness, `datetime`, weekly | 100% (8/8) | 75% (6/8) |
| Constant features | `family`, `model_id`, `variable` | those three, plus `site_id` and `horizon` |
| Max pairwise correlation | `crps` ~ `mean` = 1.0 | same, and it is the only numeric pair |

Skewness on the slice: `crps` and `mean` about 1.27. Kurtosis (excess) about
3.77 for both. `observation` drops out of skewness, kurtosis, and the
correlation list because its non-null values are a single number.

The weekly gap on the slice is 2024-06-24 and 2024-07-01. Range reported by
the metric: 2024-06-03 through 2024-07-22.

---

## B. Live: one ecoforecast scores object

Same hand-off, after the catalog step. One parquet object. Stay on
ecoforecast.

**Prompt**

```text
Endpoint https://qlever.geocodes-aws.earthcube.org/graphspace/ecoforecast.

1. forecast-parquet list --contains 'variable=amblyomma_americanum/model_id=tg_tbats' --limit 5
2. forecast-parquet horizon on that scores URL, site TALL, no --lead.
   This prints the lead table and does not write a PNG.
3. Choose the shortest positive whole-day lead whose duplicate_targets is 0
   and whose scored_rows is at least 5. If none qualify, stop and say so.
4. The CLI prints `selected object: <key>`. The local file is
   /tmp/decoder-pi- plus that key with every "/" replaced by "_".
   Confirm the file exists. Pass that absolute path to AIDRIN.
   Do not pass the s3:// or https:// URL.
5. With PyArrow, write /tmp/decoder-pi-aidrin-slice.parquet containing only
   site TALL and that lead. Lead is the whole-day difference
   datetime minus reference_datetime. Use a `horizon` column only when the
   file actually has one. Do not average rows that share a target date.
6. On the slice, run the same AIDRIN calls as the offline example:
   summarize_dataset, run_data_quality_check, row-level-completeness,
   duplicity-by-features on datetime,site_id, temporal-completeness on
   datetime, and the four structure metrics. Set frequency from the usual
   step between target dates (often W). The lead length is not the frequency.
7. Write runs/aidrin-live-slice.md.

Report model, variable, site, lead in days, row count, and the scores.
CRPS is the value neon4cast stored. The report covers this one file.
Leave the ready-or-not judgment to the reader.
Do not run fairness, privacy, feature-relevance, or the agentic tools.
Download one parquet. Do not query deepoceans or earthsurface.
```

**Skills:** `forecast-parquet` (`list`, `horizon`) then the same MCP tools.

**Expect:** a lead table, a slice path under `/tmp`, and a markdown report
whose temporal-completeness and duplicate-feature checks describe that slice.
A handful of target dates does not support a seasonal claim. If the object is
over 80 MiB, the harness refuses the download; say so and stop.

---

## Reading the scores

Higher completeness is a larger share of non-null values. Higher duplicity and
higher outlier rates are larger shares of duplicated or extreme values. AIDRIN
states that direction in each payload's `Description` where it has one. Quote
the number and the column. A constant `model_id` on a one-model slice is the
filter you asked for. An outlier CRPS is a large stored score, which still
needs a domain reading.

The report is advisory. AIDRIN does not check that a CRPS was computed
correctly, and this harness does not recompute it either.
