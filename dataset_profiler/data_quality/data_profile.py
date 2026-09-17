import io
import unicodedata
from collections import Counter

import pandas as pd

# A column with at most this many distinct values is treated as categorical and
# gets its full value counts, so every variant spelling is visible to the model
# rather than only the ones that happen to land in the random sample.
MAX_CATEGORICAL_DISTINCT = 30
# Share of non-empty values that must parse as numbers for a column to be treated
# as numeric. Not 1.0, so that a handful of stray non-numeric entries -- often the
# very errors being looked for -- do not hide the column's numeric range.
NUMERIC_SHARE = 0.95
# Shapes reported per text column; more than this is summarised as "varied".
MAX_SHAPES = 5
# Case/accent variant groups reported per column.
MAX_VARIANT_GROUPS = 5


def value_shape(value: str) -> str:
    """Reduce a value to its character classes.

    Digits become 9, letters A or a, everything else is kept. Letter runs
    collapse, so names of any length share a shape, but digit runs do not: digit
    counts are exactly what tell "2025-03-01" apart from "01/03/2025", or
    "S2024-00123" from "2400123".
    """
    out = []
    for ch in value:
        if ch.isdigit():
            c = "9"
        elif ch.isalpha():
            c = "A" if ch.isupper() else "a"
        else:
            c = ch
        if c in ("A", "a") and out and out[-1] == c:
            continue
        out.append(c)
    return "".join(out)


def _variant_key(value: str) -> str:
    """Case- and accent-insensitive key, grouping "Athens" with "ATHENS"."""
    folded = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(c for c in folded if not unicodedata.combining(c))


def _column_signals(values: pd.Series) -> dict:
    """Deterministic evidence about one column, computed over every row.

    The model otherwise sees 100 sampled rows, so an issue affecting 2% of a
    table is missed about as often as it is caught, and the model has no way to
    count how many rows a problem affects. These signals give it both.
    """
    non_empty = values[values.str.strip() != ""]
    if non_empty.empty:
        return {"kind": "empty"}

    numbers = pd.to_numeric(non_empty, errors="coerce")
    parsed = numbers.notna()
    if parsed.mean() >= NUMERIC_SHARE:
        non_numeric = Counter(non_empty[~parsed])
        return {
            "kind": "numeric",
            "min": float(numbers.min()),
            "max": float(numbers.max()),
            "negative_count": int((numbers < 0).sum()),
            "non_numeric_values": dict(non_numeric.most_common(5)),
        }

    signals = {}
    counts = Counter(non_empty)
    if len(counts) <= MAX_CATEGORICAL_DISTINCT:
        signals["kind"] = "categorical"
        signals["value_counts"] = dict(counts.most_common())
    else:
        signals["kind"] = "text"
        shapes = Counter(value_shape(v) for v in non_empty)
        signals["shape_count"] = len(shapes)
        signals["shapes"] = dict(shapes.most_common(MAX_SHAPES))

    groups = {}
    for raw, n in counts.items():
        groups.setdefault(_variant_key(raw), {})[raw] = n
    variants = sorted(
        (g for g in groups.values() if len(g) > 1),
        key=lambda g: -sum(g.values()),
    )
    if variants:
        signals["case_variant_groups"] = variants[:MAX_VARIANT_GROUPS]
    return signals


def build_profile(df: pd.DataFrame, sample_size: int = 100) -> dict:
    """Build a compact data profile for the LLM including a random sample.

    The dataframe is expected to hold every column as a string
    (``dtype=str, keep_default_na=False``) so that the original formatting
    of the values is preserved for error detection.
    """
    sample = df.sample(n=min(sample_size, len(df)), random_state=None).reset_index(
        drop=True
    )

    columns_meta = {}
    for col in df.columns:
        non_empty = df[col][df[col].str.strip() != ""]
        unique_vals = non_empty.unique()
        columns_meta[col] = {
            "total_rows": len(df),
            "empty_count": int((df[col].str.strip() == "").sum()),
            "unique_count": int(non_empty.nunique()),
            "sample_distinct_values": unique_vals[:20].tolist(),
            "signals": _column_signals(df[col]),
        }

    buf = io.StringIO()
    sample.to_csv(buf, index=False)
    sample_csv = buf.getvalue()

    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "columns_meta": columns_meta,
        "sample_csv": sample_csv,
        "sample_size": len(sample),
    }
