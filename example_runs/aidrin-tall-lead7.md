# AIDRIN offline: synthetic TALL lead 7

No SPARQL. No parquet download. Fixture only.

AIDRIN **2026.8.2**. `list_metrics` reported `mlflow_enabled: false`, so `start_assessment` / `end_assessment` were not called. No `endpoint` or `profile`. Fairness, privacy, feature-relevance, class-imbalance, k-anonymity, HIPAA, and agentic tools were not run.

The fixture is one model (`tg_tbats`), one variable (`amblyomma_americanum`), two sites, and three leads. AIDRIN scored **one series**: site TALL, `horizon == 7`.

## Paths

| File | Path | Rows |
| --- | --- | --- |
| Unfiltered fixture | `skills/forecast-parquet/fixtures/scores_horizon.parquet` | 12 × 10 |
| Slice (`site_id == TALL` and `horizon == 7`) | `/tmp/decoder-pi-aidrin-tall-lead7.parquet` | **6** × 10 |

The slice keeps every column. The 2024-07-22 score row was left null (not filled).

## `summarize_dataset` (unfiltered fixture)

```json
{
  "shape": {"rows": 12, "columns": 10},
  "columns": [
    "reference_datetime", "site_id", "datetime", "family", "model_id",
    "variable", "observation", "crps", "mean", "horizon"
  ],
  "numerical": {
    "observation": {
      "count": 11, "mean": 20.0, "std": 0.0, "min": 20.0,
      "25%": 20.0, "50%": 20.0, "75%": 20.0, "max": 20.0, "missing": 1
    },
    "crps": {
      "count": 11, "mean": 23.636363636363637, "std": 13.917778035826892,
      "min": 9.0, "25%": 13.75, "50%": 19.0, "75%": 29.0, "max": 55.0, "missing": 1
    },
    "mean": {
      "count": 11, "mean": 24.636363636363637, "std": 13.917778035826892,
      "min": 10.0, "25%": 14.75, "50%": 20.0, "75%": 30.0, "max": 56.0, "missing": 1
    },
    "horizon": {
      "count": 12, "mean": 8.208333333333334, "std": 3.951169753913697,
      "min": 0.5, "25%": 7.0, "50%": 7.0, "75%": 8.75, "max": 14.0, "missing": 0
    }
  },
  "categorical": {
    "site_id": {"count": 12, "unique": 2, "top": "TALL", "freq": 10, "missing": 0},
    "family": {"count": 12, "unique": 1, "top": "normal", "freq": 12, "missing": 0},
    "model_id": {"count": 12, "unique": 1, "top": "tg_tbats", "freq": 12, "missing": 0},
    "variable": {"count": 12, "unique": 1, "top": "amblyomma_americanum", "freq": 12, "missing": 0}
  }
}
```

`reference_datetime` and `datetime` appear in `columns` and not in the numeric or categorical stat blocks. `observation`, `crps`, and `mean` each have one missing value. Non-null `observation` is 20 everywhere.

## Slice rows (TALL, horizon 7)

| `datetime` | `reference_datetime` | `observation` | `crps` | `mean` | `horizon` |
| --- | --- | --- | --- | --- | --- |
| 2024-06-03 | 2024-05-27 | 20 | 12.0 | 13.0 | 7 |
| 2024-06-10 | 2024-06-03 | 20 | 18.5 | 19.5 | 7 |
| 2024-06-17 | 2024-06-10 | 20 | 11.0 | 12.0 | 7 |
| 2024-07-08 | 2024-07-01 | 20 | 40.0 | 41.0 | 7 |
| 2024-07-15 | 2024-07-08 | 20 | 15.5 | 16.5 | 7 |
| 2024-07-22 | 2024-07-15 | null | null | null | 7 |

## Slice scores

### `run_data_quality_check`

```json
{
  "completeness": {
    "Completeness scores": {
      "reference_datetime": 1.0,
      "site_id": 1.0,
      "datetime": 1.0,
      "family": 1.0,
      "model_id": 1.0,
      "variable": 1.0,
      "observation": 0.8333333333333334,
      "crps": 0.8333333333333334,
      "mean": 0.8333333333333334,
      "horizon": 1.0
    },
    "Overall Completeness": 0.95
  },
  "duplicity": {
    "Duplicity scores": {"Overall duplicity of the dataset": 0.0}
  },
  "outliers": {
    "Outlier scores": {
      "observation": 0.0,
      "crps": 0.2,
      "mean": 0.2,
      "horizon": 0.0,
      "Overall outlier score": 0.1
    }
  }
}
```

`crps` / `mean` / `observation` completeness is 5 of 6 rows (0.8333). The `crps` and `mean` outlier rate 0.2 is the 40 / 41 pair on 2024-07-08. `horizon` outlier rate is 0 because every row is lead 7.

### `row-level-completeness`

`required_columns=datetime,site_id,crps,mean,observation`

```json
{
  "Row-Level Completeness (%)": 83.33333333333334,
  "Complete rows": 5,
  "Total rows": 6,
  "Description": "Percentage of rows where every required column is non-null."
}
```

### `duplicity-by-features` (`datetime,site_id`)

```json
{
  "Duplicate count": 0,
  "Duplicate percentage": 0.0,
  "Total rows": 6,
  "Duplicate groups": []
}
```

### `temporal-completeness` (`datetime`, `W`)

```json
{
  "Temporal Completeness (%)": 75.0,
  "Frequency": "W",
  "Expected intervals": 8,
  "Present intervals": 6,
  "Range start": "2024-06-03 00:00:00+00:00",
  "Range end": "2024-07-22 00:00:00+00:00"
}
```

Missing weeks: 2024-06-24 and 2024-07-01 (the three-week gap between 2024-06-17 and 2024-07-08).

### `constant-feature-count`

```json
{
  "Constant feature count": 5,
  "Total features": 10,
  "Constant features": {
    "site_id": "TALL",
    "family": "normal",
    "model_id": "tg_tbats",
    "variable": "amblyomma_americanum",
    "horizon": 7.0
  }
}
```

### `max-pairwise-correlation`

```json
{
  "Max Pairwise Correlation": 1.0,
  "Most Correlated Pair": "crps ~ mean",
  "Top Correlated Pairs": [{"pair": "crps ~ mean", "correlation": 1.0}],
  "Numeric Features Considered": 2
}
```

`observation` is a single non-null value (20), so it drops out of the numeric pair list. `horizon` is constant.

### `skewness`

```json
{
  "Skewness": {"crps": 1.9036091786498852, "mean": 1.9036091786498852},
  "Most Skewed Feature": "crps",
  "Max Absolute Skewness": 1.9036091786498852,
  "Numeric Features Considered": 2
}
```

### `kurtosis`

```json
{
  "Kurtosis": {"crps": 3.767567415041645, "mean": 3.767567415041645},
  "Most Extreme Kurtosis Feature": "crps",
  "Max Absolute Excess Kurtosis": 3.767567415041645,
  "Numeric Features Considered": 2
}
```

## Contrast: unfiltered fixture

Same two metrics on the 12-row file (two sites, leads 0.5 / 7 / 14):

**`temporal-completeness` (`datetime`, `W`)** — 100% (8 of 8 weeks, 2024-06-03 through 2024-07-22).

**`duplicity-by-features` (`datetime,site_id`)** — 2 groups, 16.7% (2 of 12): TALL on 2024-06-03 (lead 0.5 and lead 7) and TALL on 2024-06-17 (lead 7 and lead 14).

Those two calls hide the mixture. Weekly completeness looks full because lead-14 rows occupy 2024-06-24 and 2024-07-01, which are the weeks the TALL lead-7 series skips. Feature duplicity looks like republished targets; it is two leads on the same site and date. On the slice, temporal completeness is 75% and `duplicity-by-features` is 0.

## Reading

CRPS is the stored neon4cast column. These commands do not recompute it.

The 2024-07-22 row has null `observation`, `crps`, and `mean`. That is the incomplete row.

Weekly temporal completeness on the slice counts gaps between target dates. Lead 7 means the forecast was issued 7 days before the target. The frequency argument is the spacing of those target dates (`W`).

`family`, `model_id`, `variable`, `site_id`, and `horizon` are constant because the slice is one identity. That is expected.

`crps` and `mean` correlate at 1 because this fixture set `mean = crps + 1`. That construction comes before calling them redundant features.

Whether the slice is AI-ready is left to the reader.
