# AIDRIN live slice: neon4cast `tg_tbats` × `amblyomma_americanum` × TALL × lead 36

One ecoforecast scores object. CRPS is the value neon4cast stored in the parquet;
nothing here recomputes it. The report covers this one file. AIDRIN **2026.8.2**
(`mlflow_enabled: false`; no `start_assessment`). Fairness, privacy,
feature-relevance, and agentic tools were not run.

## What was scored

| Field | Value |
| --- | --- |
| Model | `tg_tbats` |
| Variable | `amblyomma_americanum` |
| Site | TALL |
| Lead | 36 whole days (`datetime` − `reference_datetime`) |
| Slice rows | 86 |
| Numeric CRPS rows | 5 |
| `horizon` column | absent |

**Catalog URL** (SPARQL only; not passed to AIDRIN):

`s3://anonymous@bio230014-bucket01/challenges/scores/bundled-parquet/project_id=neon4cast/duration=P1W/variable=amblyomma_americanum/model_id=tg_tbats?endpoint_override=sdsc.osn.xsede.org`

**Selected object:** `challenges/scores/bundled-parquet/project_id=neon4cast/duration=P1W/variable=amblyomma_americanum/model_id=tg_tbats/data_0.parquet` (717729 bytes)

**Local download (AIDRIN input source):**  
`/tmp/decoder-pi-challenges_scores_bundled-parquet_project_id=neon4cast_duration=P1W_variable=amblyomma_americanum_model_id=tg_tbats_data_0.parquet`

**Slice written with PyArrow (AIDRIN `file_path`):**  
`/tmp/decoder-pi-aidrin-slice.parquet`

`list --contains 'variable=amblyomma_americanum/model_id=tg_tbats' --limit 5` returned 0 URLs (SPARQL `LIMIT` is applied before the substring filter). Raising the SPARQL fetch found the scores prefix above. One parquet object was downloaded. No deepoceans or earthsurface query.

## Lead choice

`forecast-parquet horizon` on that URL, site TALL, no `--lead`, printed scored-row counts (numeric `crps` only). Shortest **positive** whole-day lead with `duplicate_targets` 0 and `scored_rows` ≥ 5:

| lead_days | scored_rows | sites | target_dates | duplicate_targets |
| --- | --- | --- | --- | --- |
| 36 | 5 | 1 | 5 | 0 |

Leads 1, 8, 15, 22, and 29 are shorter but have fewer than 5 scored rows. The slice keeps every TALL row at lead 36 (including rows with null `crps`). Rows that share a target date were not averaged.

Usual step between target dates is 7 days, so temporal completeness uses `frequency=W`. The 36-day lead is not the frequency.

## Stored CRPS (five non-null rows)

| target (`datetime`) | `reference_datetime` | `observation` | `crps` | `mean` |
| --- | --- | --- | --- | --- |
| 2024-08-05 | 2024-06-30 | 23.431 | 15.593 | 29.387 |
| 2025-06-16 | 2025-05-11 | 22.222 | 10.813 | 16.888 |
| 2025-07-07 | 2025-06-01 | 20.126 | 20.743 | 6.581 |
| 2025-07-21 | 2025-06-15 | 29.907 | 22.916 | 6.579 |
| 2025-08-11 | 2025-07-06 | 44.291 | 27.418 | 6.577 |

Min stored CRPS 10.813; max 27.418. Five target dates do not support a seasonal claim.

## `summarize_dataset`

Shape 86 × 15. Columns: `reference_datetime`, `site_id`, `datetime`, `family`, `pub_datetime`, `observation`, `crps`, `logs`, `mean`, `median`, `sd`, `quantile97.5`, `quantile02.5`, `quantile90`, `quantile10`.

`reference_datetime`, `datetime`, and `pub_datetime` appear in `columns` and not in the numeric or categorical stat blocks.

| column | count | missing | notes |
| --- | --- | --- | --- |
| `site_id` | 86 | 0 | TALL only |
| `family` | 86 | 0 | `normal` only |
| `observation` | 5 | 81 | mean 28.00 |
| `crps` | 5 | 81 | mean 19.50 |
| `logs` | 5 | 81 | |
| `mean` / `median` | 86 | 0 | identical stats in this file |
| `sd` and quantiles | 86 | 0 | |

## Data quality

### `run_data_quality_check`

Overall completeness **0.775**. Column completeness: identity and timestamp columns 1.0 except `pub_datetime` **0.453**; `observation` / `crps` / `logs` **0.058** (5 of 86); forecast-summary columns 1.0.

Identical-row duplicity **0**.

Outlier rates (AIDRIN IQR on non-null values): `observation` 0.2; `crps` 0; `logs` 0; `mean` and `median` 0.151; overall outlier score **0.083**. An outlier CRPS would be a large stored score; on this slice the five CRPS values were not flagged.

### `row-level-completeness`

`required_columns=datetime,site_id,crps,mean,observation`

- Row-level completeness **5.81%**
- Complete rows **5** / total **86**

Those five are the rows that still have a stored CRPS and observation.

### `duplicity-by-features`

`duplicate_columns=datetime,site_id`

- Duplicate count **34**
- Duplicate percentage **39.5%**
- 34 target dates appear twice (typically one row with `pub_datetime` set and one without; `crps` null on both). The five scored targets are not in those pairs.
- `horizon` CLI `duplicate_targets` 0 counts **scored** rows only. The slice includes the null-CRPS copies, which this metric sees.

### `temporal-completeness`

`timestamp_column=datetime`, `frequency=W`

- Temporal completeness **39.4%**
- Expected intervals **132**, present **52**
- Range 2023-02-06 through 2025-08-11

Weekly gaps are gaps between **target** dates. After a run of 7-day steps in 2023, the calendar jumps (224 d, then 315 d, then 21 / 14 / 21 d). Those empty weeks dominate the 132 expected intervals.

## Structure

### `constant-feature-count`

2 of 15 columns: `site_id` = TALL, `family` = `normal`. Expected for a one-site slice. `model_id` and `variable` are not columns in this object; they live in the OSN key.

### `max-pairwise-correlation`

Max **1.0** for `mean ~ median` (the pair is identical in this file). Next: `quantile02.5 ~ quantile10` 0.999; `logs ~ sd` 0.998; `quantile97.5 ~ quantile90` 0.997. AIDRIN’s description treats values near 1 as redundant features; `mean` and `median` are the same numbers here.

### `skewness`

Most skewed: `mean` (and `median`) **−3.12**. `crps` **−0.27** (5 values). `observation` **1.57**.

### `kurtosis`

Most extreme: `mean` / `median` excess kurtosis **10.54**. `crps` **−0.80**. `observation` **2.23**.

## Reading the scores

Higher completeness is a larger share of non-null values. Higher duplicity and higher outlier rates are larger shares of duplicated or extreme values. A constant `site_id` is the TALL filter. AIDRIN does not check that a CRPS was computed correctly, and this harness does not recompute it.

Whether this slice is AI-ready is left to the reader.
