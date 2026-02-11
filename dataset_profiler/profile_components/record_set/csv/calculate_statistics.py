import pandas as pd

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics


def calculate_column_statistics(column: pd.Series) -> ColumnStatistics:
    """Calculate statistics for a given pandas Series (column)."""
    if len(column) > 0:
        if pd.api.types.is_numeric_dtype(column):
            non_na = column.dropna()
            if len(non_na) == 0:
                # If all values are NA, we can't calculate statistics
                return ColumnStatistics(
                    row_count=0,
                    mean=None,
                    median=None,
                    standard_deviation=None,
                    min_value=None,
                    max_value=None,
                    missing_count=int(column.isna().sum()),
                    missing_percentage=float(column.isna().sum() / len(column) * 100),
                    histogram=[],
                    unique_count=0,
                )
            histogram = pd.cut(column.dropna(), bins=10).value_counts().sort_index()
            bins = list(histogram.index)
            histogram_dict = [
                {
                    "binRange": [float(bin_range.left), float(bin_range.right)],
                    "count": int(val),
                } for bin_range, val in zip(bins, list(histogram))
            ]
            stats = ColumnStatistics(
                row_count=int(column.count()),
                mean=float(column.mean()),
                median=float(column.median()),
                standard_deviation=float(column.std()),
                min_value=float(column.min()),
                max_value=float(column.max()),
                missing_count=int(column.isna().sum()),
                missing_percentage=float(column.isna().sum() / len(column) * 100),
                histogram=histogram_dict,
                unique_count=int(column.nunique()),
            )
        else:
            stats = ColumnStatistics(
                row_count=int(column.count()),
                missing_count=int(column.isna().sum()),
                missing_percentage=float(column.isna().sum() / len(column) * 100),
                unique_count=int(column.nunique()),
            )
    else:
        stats = ColumnStatistics()

    return stats
