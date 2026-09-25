# AIDRIN: CCHDO OMEX2 bottle file

One deepoceans `schema:distribution`. AIDRIN **2026.8.2**
(`mlflow_enabled: false`). Fairness, privacy, and the agentic tools were not run.
The ready-or-not judgment is left open. AIDRIN does not check that the bottle
values are the ones the cruise measured.

## Where the file came from

SPARQL endpoint `https://qlever.geocodes-aws.earthcube.org/graphspace/deepoceans`.

| Field | Value |
| --- | --- |
| Dataset name | Hydrographic Cruise OMEX2: Bottle Dataset |
| `encodingFormat` | `text/csv` |
| `contentUrl` | `https://cchdo.ucsd.edu/data/49/OMEX2_hy1.csv` |
| Raw download | `/tmp/decoder-pi-aidrin-dist/OMEX2_hy1.csv` (458 KiB) |
| File scored | `/tmp/decoder-pi-aidrin-dist/OMEX2_bottle.csv` (2,016 × 33) |
| Dated copy | `/tmp/decoder-pi-aidrin-dist/OMEX2_bottle_dated.csv` (`sample_date` added) |

The catalog calls this `text/csv`. The bytes are a WHP exchange file: a
`BOTTLE,…` stamp, `#` comments, a parameter header beginning `EXPOCODE,`, a
units line, data, and `END_DATA`. AIDRIN's CSV reader rejects the raw file:

`Error tokenizing data. C error: Expected 2 fields in line 34, saw 3`

The scored file keeps the `EXPOCODE` header, drops the units line and the
comments, stops before `END_DATA`, and maps `-999` to null. The exchange
comments say station, cast, and bottle numbers were fabricated, bottom depth
was estimated from global topography, and pressure was computed from depth.
Those sentences are not in the table AIDRIN scored.

## What the table is

2,016 bottles, one cruise code (`EXPOCODE` `OMEX2`, with leading spaces),
`CASTNO` always 1. Dates run from 19970620 through 19990917 (68 distinct
days). Latitude 36.55–47.76, longitude −10.64 to −7.08. Gulf of Biscay and
the Iberian margin, as the comment block says.

Physical columns are nearly filled. Bottle nutrients are not.

| Column | Non-null rows | Completeness |
| --- | --- | --- |
| `CTDTMP` | 2,009 | 0.997 |
| `CTDSAL` / `THETA` | 2,007 | 0.996 |
| `CTDPRS`, position, `DATE`, `DEPTH` | 2,016 | 1.0 |
| `OXYGEN` | 1,367 | 0.678 |
| `CTDOXY` | 1,353 | 0.671 |
| `ALKALI` | 1,366 | 0.678 |
| `PHSPHT` | 1,328 | 0.659 |
| `SILCAT` | 1,018 | 0.505 |
| `NITRAT` | 669 | 0.332 |
| `NITRIT` | 670 | 0.332 |
| `AMMONI` | 578 | 0.287 |
| Bottle `SALNTY` | 322 | 0.160 |
| `UREA` | 226 | 0.112 |

Every `*_FLAG_W` column is completeness 1.0. WOCE flag 9 means the measurement
was not reported, and it is stored as the number 9, so the flag column stays
full while the measurement is null. `SALNTY_FLAG_W` has median 9. `UREA_FLAG_W`
has median 9.

## Data quality

`run_data_quality_check`

- Overall completeness **0.830**. That average includes the flag columns and the identifier columns.
- Identical-row duplicity **0**.
- Overall IQR outlier rate **0.031**. Highest measurement rates: `CTDPRS` 0.157, `ALKALI` 0.146, `LATITUDE` 0.132, bottle `SALNTY` 0.115, `LONGITUDE` 0.094, `UREA` 0.071, `NITRIT` 0.064, `CTDSAL` 0.062. `NITRAT` outlier rate is 0. `NITRAT` still has a minimum of −0.02.

`row-level-completeness`

| Required columns | Complete rows | Percent |
| --- | --- | --- |
| `DATE`, `LATITUDE`, `LONGITUDE`, `CTDPRS`, `CTDTMP`, `CTDSAL` | 2,007 / 2,016 | 99.6% |
| `CTDTMP`, `CTDSAL`, `OXYGEN`, `NITRAT`, `PHSPHT`, `SILCAT` | 539 / 2,016 | 26.7% |

`duplicity-by-features` on `EXPOCODE,STNNBR,CASTNO,BTLNBR`: **0**. Each bottle id occurs once. The exchange comment says those ids were fabricated, so uniqueness is uniqueness of the assigned key.

`temporal-completeness` on `sample_date`, frequency `D`: **8.3%** (68 of 820 days, 1997-06-20 through 1999-09-17). The occupied days are cruise days. The empty days are the gaps between cruises.

## Structure

`constant-feature-count`: 2 of 33. `EXPOCODE` = `OMEX2`, `CASTNO` = 1.

`max-pairwise-correlation`: **0.9999** for `CTDTMP` ~ `THETA`. Next: `NITRAT_FLAG_W` ~ `NITRIT_FLAG_W` 0.999, `CTDSAL` ~ `SALNTY` 0.998, `OXYGEN_FLAG_W` ~ `ALKALI_FLAG_W` 0.962, `NITRAT` ~ `PHSPHT` 0.956.

`skewness`: the most skewed column is `CTDSAL_FLAG_W` at **14.88**. Among measurements, `AMMONI` 6.21, `UREA` 4.65, `NITRIT` 2.87, `CTDPRS` 2.75, `SILCAT` 2.30, `CTDSAL` −1.77.

`kurtosis` (excess): `CTDSAL_FLAG_W` **219.6**. Among measurements, `AMMONI` 50.5, `UREA` 20.8, `CTDSAL` 17.8, `SILCAT` 11.3, `NITRIT` 10.5, `CTDPRS` 9.88.

## Impact on AI

`feature-relevance`, target `NITRAT`, numeric features `CTDPRS`, `CTDTMP`, `CTDSAL`, `LATITUDE`, `LONGITUDE`, categorical `EXPOCODE`. AIDRIN drops rows with missing values and reports Pearson correlation with the target:

| Feature | Correlation with `NITRAT` |
| --- | --- |
| `CTDTMP` | −0.886 |
| `CTDPRS` | 0.791 |
| `LATITUDE` | 0.205 |
| `LONGITUDE` | −0.065 |
| `CTDSAL` | −0.060 |

`EXPOCODE` does not appear in the coefficient list. The coefficients describe the bottles that have a nitrate value (669 rows), not all 2,016.

## Reading

For a CTD profile table (pressure, temperature, salinity, position, date), row-level completeness is 99.6% and bottle keys do not repeat. That is the part of this file a model can use without first inventing measurements.

For a row that also has oxygen, nitrate, phosphate, and silicate, row-level completeness is 26.7%. Urea, ammonium, and bottle salinity are sparser still. Overall completeness of 0.83 counts the QC flags as present.

`CTDTMP` and `THETA` are the same temperature (potential temperature is computed from the in-situ value). `CTDSAL` and bottle `SALNTY` agree where both exist. Using both members of either pair as features repeats one signal. Nitrate and phosphate move together (0.96); if nitrate is the target, phosphate is a second nutrient, not a physical driver.

The skewness and kurtosis champions are flag columns. A WOCE flag that is usually 2 and sometimes 9 is a two-point code. Pressure, silicate, nitrite, ammonium, and urea carry the heavy measurement tails. The pressure outlier rate is the deep end of the casts (pressure max 4,114 dbar). The latitude outlier rate is the geographic spread of the cruises.

Daily temporal completeness of 8.3% is the cruise calendar: 68 days with bottles inside a 820-day span. A daily time-series model and a bottle-profile model are different uses of this file.

Nitrate's correlation with temperature (−0.89) and pressure (0.79) is the shelf pattern in the scored rows: colder, deeper bottles have higher nitrate. That is a Pearson coefficient after dropping empty nitrate rows. It is not a trained model, and it ignores the exchange note that some of the keys and the bottom depth were filled in rather than measured.
