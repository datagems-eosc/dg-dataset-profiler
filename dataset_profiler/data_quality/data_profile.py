import io

import pandas as pd


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
