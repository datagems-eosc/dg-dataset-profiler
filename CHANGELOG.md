# Changelog

## Unreleased

### Fixed: column statistics, types, samples and checksums

The structure of the profile is unchanged: the same keys, nesting, `@type`s and `@context`. Only values change. The rules are shared with croissant-laminate; see [Column Statistics](docs/docs/column-statistics.md).

- **Median and the 5th/95th percentiles are exact.** They were interpolated from the 10-bin histogram, which was far off on skewed data (a column of 990 × `1` and 10 × `1,000,000` reported a median of 50,011). Above 20 million numeric values per file they come from a t-digest.
- **Variance and standard deviation are exact** for columns whose mean is large compared with their spread. They used to come out as `0`.
- **`uniqueCount` is exact**, or `null` when a column has too many distinct values to count within the budget. It used to stop counting silently near 100,000, and could report up to 500,000.
- **Column types are decided from every value**, not from 3 random rows. `true`/`false` columns are `sc:Boolean` (they were `sc:Float`). Columns with a leading zero (`01234`) or a few non-numeric values are `sc:Text`, with null numeric statistics, as for any text column. Integer columns with missing values are `sc:Integer` (they were `sc:Float`).
- **Samples are deterministic and hold no missing values.** They are seeded from the file's content and the column's name. Leading-zero columns sample strings (`"01234"`).
- **`sha256` of a file is the hash of its content.** It was the hash of its path.
- **`includes` of a nested file set holds its whole path** (`a/b/*`, not `b/*`).
- **Excel sheet FileObjects carry the right sheet name.** A skipped empty or unreadable sheet used to shift the names of every later sheet.
- **Database samples of `jsonb` and array columns are JSON** (`{"k": 702}`). They were Python reprs (`{'k': 702}`).
- Malformed CSV rows (skipped or padded by pandas) are counted and logged with their line numbers.
- A warning is logged when a request's database host and port differ from the ones the profiler connects with. The profile still records the request's values.

New dependency: `fastdigest` (`>=0.14,<0.15`). Python 3.10 or later is required (the code already used 3.10 syntax).

### Existing profiles

Profiles created before this release have approximate (histogram-interpolated) medians and percentiles, possibly zero variance for large-valued columns, capped unique counts, `sc:Float` booleans and path-based checksums. They are not regenerated automatically. Editing a dataset re-profiles it with the fixed code. The structure of the profile is unchanged.
