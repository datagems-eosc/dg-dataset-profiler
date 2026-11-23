# Column Statistics

Every column of a CSV file, an Excel sheet, a JSON field or a database table gets a `dg:ColumnStatistics` node. This page says how its values are computed, so they can be read correctly and compared across files.

The rules are shared with [croissant-laminate](https://github.com/datagems-eosc/croissant-laminate), the standalone profiler: both give the same values for the same data. Their constants live in `dataset_profiler/profile_components/record_set/csv/calculate_statistics.py` and have the same names and values in both.

Every statistics key is always present. A key with no value is `null`; no key is ever left out.

## How a CSV file is read

A file is read three times, each time streamed, so memory stays bounded whatever its size:

1. **The string pass** (`csv.reader`) sees every raw value. It decides each column's type, keeps a sample of the original strings and counts malformed rows.
2. **The typed pass** (pandas) gathers the statistics. Chunks are sized by cells, not rows (`CHUNK_CELLS = 2,000,000`; at least 1,000 rows per chunk), so wide files stay within memory. Numeric columns keep pandas' types. The other columns are read as text, so `01234` keeps its leading zero.
3. **The histogram pass** bins numeric and boolean columns once their minimum and maximum are known.

Excel sheets are written to a temporary CSV each and read the same way. Empty sheets are skipped.

## Types

A raw value is **missing** if it is empty or one of pandas' default NA strings (`NA`, `N/A`, `NULL`, `NaN`, `None`, `null`, `nan`, `#N/A`, …). The list is spelled out in the code as `NA_TOKENS`, so it doesn't change with the pandas version.

Each non-missing value is matched against these classes:

| Class | Matches | `dataType` |
|---|---|---|
| bool | `true`, `false`, any case | `sc:Boolean` |
| int | `12`, `-3`, `0` (no leading zero) | `sc:Integer` |
| float | `1.5`, `.5`, `1e-3`, and any int | `sc:Float` |
| date | `2024-01-31` | `sc:Date` |
| datetime | `2024-01-31T10:00`, `2024-01-31 10:00:00.5+02:00` | `sc:DateTime` |

A column takes the **first class, in that order, that every non-missing value matches**; otherwise it is `sc:Text`. Every value counts, not a sample:

- `1, 2, , 4` → `sc:Integer` (missing values don't matter);
- `1, 2.5` → `sc:Float`;
- `0, 1, 1` → `sc:Integer`;
- `01234, 00012` → `sc:Text` (a leading zero is neither int nor float);
- 395 numbers and 5 words → `sc:Text`;
- an all-missing column → `sc:Text`.

JSON values keep their JSON types. A JSON text field is `sc:Date` (or `sc:DateTime`) when every one of its values is an ISO 8601 date (date-time).

## Statistics

Numeric statistics (`mean`, `median`, `standardDeviation`, `variance`, `min`, `max`, `range`, `percentile05`, `percentile95`, `histogram`) are computed for `sc:Integer`, `sc:Float` and `sc:Boolean` columns. A text column has them all `null`, and carries `rowCount`, `missingCount`, `missingPercentage` and `uniqueCount` only.

| Statistic | How |
|---|---|
| `rowCount`, `missingCount`, `missingPercentage` | Exact. `rowCount` counts non-missing values |
| `mean`, `min`, `max`, `range` | Exact |
| `variance`, `standardDeviation` | Exact, sample variance (`n − 1`). Merged across chunks with Chan's parallel formula, which stays exact when the mean is large compared with the spread. `NaN` for a single value |
| `median`, `percentile05`, `percentile95` | Exact (`numpy.quantile`, linear interpolation) while a file holds at most `EXACT_VALUES_PER_FILE = 20,000,000` numeric values in total. Above that, every numeric column of the file switches to a t-digest (`fastdigest`, 1000 centroids), fed in file order, so the estimate is reproducible. The profiler's log lists the columns whose quantiles are estimates |
| `uniqueCount` | Exact, from 64-bit hashes of the values, within a per-file budget of `UNIQUE_HASHES_PER_FILE = 10,000,000` distinct hashes. A column whose distinct values don't fit gets `null`, never a lower bound. The log lists those columns |
| `histogram` | 10 equal-width bins between `min` and `max` |

Boolean columns count `true` as 1 and `false` as 0: `mean` is the share of `true`, `min` and `max` are 0 or 1, and `median` is the majority value (a tie gives `false`). They have no percentiles.

## Samples

`sample` holds up to 10 values per column, drawn uniformly from the non-missing values. The draw is seeded from the file's content hash (`sha256`) and the column's name, so the same file always gives the same sample, and the same sample in the platform and in laminate.

Sampled values have the column's type: numbers for numeric columns, `true`/`false` for booleans, the original strings for everything else (a leading-zero column samples `"01234"`).

### Database samples

Database tables are sampled differently:

- A column's `sample` holds **up to 3 distinct non-null values among the first 1000 rows** the database returns (`SELECT DISTINCT … LIMIT 3` over a `LIMIT 1000` subquery). They are not random. Typically they are the smallest values of those rows, so don't read them as representative of the whole table.
- `jsonb` and array values are written as JSON (`{"k": 702}`, `["a", "b"]`); other values as their text form.

## Malformed rows

pandas reads a CSV with `on_bad_lines="skip"`. The string pass counts what that does:

- a row with **more** fields than the header is skipped;
- a row with **fewer** fields is kept, padded with missing values;
- a blank line is ignored.

The counts and the line numbers of the first 10 rows of each kind are logged. They are not part of the profile. Line numbers are physical lines, so they stay right when a quoted value spans several lines.

## Profiles made before these rules

Statistics computed before these rules (see the [changelog](https://github.com/datagems-eosc/dataset-profiler/blob/main/CHANGELOG.md)) can differ. Stored profiles are not regenerated automatically. Editing a dataset re-profiles it with the current rules.
