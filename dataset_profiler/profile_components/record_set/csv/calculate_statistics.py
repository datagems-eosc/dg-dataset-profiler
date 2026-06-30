import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.utilities import find_column_type_in_csv

# Number of equal-width bins used for the reported histogram. Median and the
# 5th/95th percentiles are interpolated from these bins (see _quantile_from_hist).
HISTOGRAM_BINS = 10
# Reservoir sample size kept per column for the profile's ``sample`` field.
SAMPLE_SIZE = 10
# Upper bound on distinct values tracked per column. Once exceeded we stop
# growing the set so a high-cardinality column cannot exhaust memory; the
# reported unique_count then becomes a lower bound (see unique_count()).
UNIQUE_COUNT_CAP = 100_000


def calculate_column_statistics(column: pd.Series) -> ColumnStatistics:
    """Calculate statistics for a fully materialised pandas Series (column).

    Kept for callers that already hold a whole column in memory. The streaming
    CSV path uses :class:`_ColumnAccumulator` instead so it never materialises a
    full column.
    """
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
            min_value = float(column.min())
            max_value = float(column.max())
            # Boolean columns are numeric, but quantile() raises on them, so
            # skip the percentile statistics for them.
            is_bool = pd.api.types.is_bool_dtype(column)
            stats = ColumnStatistics(
                row_count=int(column.count()),
                mean=float(column.mean()),
                median=float(column.median()),
                standard_deviation=float(column.std()),
                min_value=min_value,
                max_value=max_value,
                missing_count=int(column.isna().sum()),
                missing_percentage=float(column.isna().sum() / len(column) * 100),
                histogram=histogram_dict,
                unique_count=int(column.nunique()),
                variance=float(column.var()),
                range_value=max_value - min_value,
                percentile05=None if is_bool else float(column.quantile(0.05)),
                percentile95=None if is_bool else float(column.quantile(0.95)),
                generated_at=datetime.now(timezone.utc).isoformat(),
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


def _to_python(value):
    """Convert a numpy/pandas scalar to a JSON-serialisable Python value."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


class _ColumnAccumulator:
    """Accumulates one CSV column's statistics across streamed chunks.

    Driven in two passes so peak memory stays bounded to a single column's
    accumulators instead of the whole file:

    * pass one (:meth:`update`) gathers counts, numeric moments, min/max, a
      capped distinct-value set and a reservoir sample;
    * pass two (:meth:`update_histogram`) bins values once the column's global
      min/max are known.

    Mean, variance, standard deviation, min, max, range, counts and the
    histogram are exact. Median and the 5th/95th percentiles are estimated from
    the histogram (:meth:`_quantile_from_hist`); unique_count is exact up to
    :data:`UNIQUE_COUNT_CAP`, beyond which it is a lower bound.
    """

    def __init__(self):
        self.total = 0          # rows seen (including NaN)
        self.missing = 0
        self.count = 0          # non-NaN values
        self.numeric = True     # AND of per-chunk numeric-ness (chunks with data)
        self.integer = True     # AND of per-chunk integer-ness (chunks with data)
        self.is_bool = False
        self.sum = 0.0
        self.sumsq = 0.0
        self.min = None
        self.max = None
        self._uniques: set = set()
        self._uniques_capped = False
        self._res_keys = np.empty(0, dtype="float64")
        self._res_vals = np.empty(0, dtype=object)
        self._edges = None
        self.hist_counts = np.zeros(HISTOGRAM_BINS, dtype=np.int64)

    # -- pass one -----------------------------------------------------------
    def update(self, series: pd.Series):
        n = len(series)
        if n == 0:
            return
        self.total += n
        na_mask = series.isna()
        n_missing = int(na_mask.sum())
        self.missing += n_missing
        non_na = series[~na_mask]
        self.count += len(non_na)

        # Reservoir sample over raw values (NaN included) to match prior behaviour.
        self._reservoir_update(series.to_numpy())

        if len(non_na) == 0:
            # An all-NaN chunk is read as float64; it must not flip a text column
            # to numeric, nor constrain the dtype of a numeric one.
            return

        is_num = pd.api.types.is_numeric_dtype(series)
        self.numeric = self.numeric and is_num
        self.integer = self.integer and pd.api.types.is_integer_dtype(series)
        if pd.api.types.is_bool_dtype(series):
            self.is_bool = True

        if not self._uniques_capped:
            self._uniques.update(non_na.unique().tolist())
            if len(self._uniques) > UNIQUE_COUNT_CAP:
                self._uniques_capped = True

        if is_num:
            vals = non_na.to_numpy(dtype="float64")
            self.sum += float(vals.sum())
            self.sumsq += float(np.square(vals).sum())
            cmin = float(vals.min())
            cmax = float(vals.max())
            self.min = cmin if self.min is None else min(self.min, cmin)
            self.max = cmax if self.max is None else max(self.max, cmax)

    def _reservoir_update(self, vals: np.ndarray):
        # Random-key reservoir: keep the SAMPLE_SIZE items with the smallest keys.
        keys = np.random.random(len(vals))
        vals = np.asarray(vals, dtype=object)
        if self._res_keys.size:
            keys = np.concatenate([self._res_keys, keys])
            vals = np.concatenate([self._res_vals, vals])
        if keys.size > SAMPLE_SIZE:
            idx = np.argpartition(keys, SAMPLE_SIZE)[:SAMPLE_SIZE]
            keys, vals = keys[idx], vals[idx]
        self._res_keys, self._res_vals = keys, vals

    # -- pass two -----------------------------------------------------------
    def needs_histogram(self) -> bool:
        return self.numeric and self.count > 0 and self.min is not None

    def update_histogram(self, series: pd.Series):
        non_na = series.dropna()
        if len(non_na) == 0:
            return
        edges = self.histogram_edges()
        cats = pd.cut(non_na, bins=edges)
        codes = cats.cat.codes.to_numpy()
        valid = codes[codes >= 0]
        if valid.size:
            self.hist_counts += np.bincount(
                valid, minlength=HISTOGRAM_BINS
            )[:HISTOGRAM_BINS]

    def histogram_edges(self) -> np.ndarray:
        if self._edges is None:
            self._edges = self._compute_edges()
        return self._edges

    def _compute_edges(self) -> np.ndarray:
        mn, mx = self.min, self.max
        if mn == mx:
            # Mirror pd.cut's handling of a degenerate range.
            adj = 0.001 * abs(mn) if mn != 0 else 0.001
            return np.linspace(mn - adj, mx + adj, HISTOGRAM_BINS + 1)
        edges = np.linspace(mn, mx, HISTOGRAM_BINS + 1)
        # pd.cut nudges the first edge outward so the minimum is included.
        edges[0] -= (mx - mn) * 0.001
        return edges

    # -- finalisation -------------------------------------------------------
    def unique_count(self) -> int:
        return len(self._uniques)

    def sample(self) -> list:
        return [_to_python(v) for v in self._res_vals.tolist()]

    def data_type(self) -> str:
        if self.numeric and self.count > 0:
            return "sc:Integer" if self.integer else "sc:Float"
        sample = self.sample()
        if len(sample) < 3:
            return "sc:Text"
        return find_column_type_in_csv(pd.Series(sample, dtype=object))

    def build_statistics(self) -> ColumnStatistics:
        if self.total == 0:
            return ColumnStatistics()

        missing_pct = float(self.missing / self.total * 100)

        if not self.numeric:
            return ColumnStatistics(
                row_count=self.count,
                missing_count=self.missing,
                missing_percentage=missing_pct,
                unique_count=self.unique_count(),
            )

        if self.count == 0:
            return ColumnStatistics(
                row_count=0,
                mean=None,
                median=None,
                standard_deviation=None,
                min_value=None,
                max_value=None,
                missing_count=self.missing,
                missing_percentage=missing_pct,
                histogram=[],
                unique_count=0,
            )

        mean = self.sum / self.count
        if self.count > 1:
            variance = (self.sumsq - self.count * mean * mean) / (self.count - 1)
            variance = max(variance, 0.0)  # guard against tiny negative fp drift
            std = math.sqrt(variance)
        else:
            variance = float("nan")  # pandas returns NaN for a single value
            std = float("nan")

        median = self._quantile_from_hist(0.5)
        p05 = None if self.is_bool else self._quantile_from_hist(0.05)
        p95 = None if self.is_bool else self._quantile_from_hist(0.95)

        return ColumnStatistics(
            row_count=self.count,
            mean=float(mean),
            median=None if median is None else float(median),
            standard_deviation=float(std),
            min_value=float(self.min),
            max_value=float(self.max),
            missing_count=self.missing,
            missing_percentage=missing_pct,
            histogram=self._histogram_dict(),
            unique_count=self.unique_count(),
            variance=float(variance),
            range_value=float(self.max - self.min),
            percentile05=None if p05 is None else float(p05),
            percentile95=None if p95 is None else float(p95),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _histogram_dict(self) -> list:
        edges = self.histogram_edges()
        return [
            {
                "binRange": [float(edges[i]), float(edges[i + 1])],
                "count": int(self.hist_counts[i]),
            }
            for i in range(HISTOGRAM_BINS)
        ]

    def _quantile_from_hist(self, q: float):
        """Estimate the q-th quantile by linear interpolation within the bin
        that holds the q-th value.

        This is an approximation whose error is bounded by the bin width. For
        heavy-tailed columns (a few extreme values stretching min/max far beyond
        the bulk of the data) the equal-width bins become very wide and the
        estimate can be off by orders of magnitude. Exact moments, min and max
        are unaffected; only median/percentiles are approximate. Swap in a
        streaming quantile sketch (e.g. t-digest) if accurate quantiles on
        skewed data are needed.
        """
        if self.count == 0 or self.min is None:
            return None
        if self.max == self.min:
            return self.min
        edges = self.histogram_edges()
        total = int(self.hist_counts.sum())
        if total == 0:
            return self.min
        target = q * total
        cumulative = 0
        for i in range(HISTOGRAM_BINS):
            c = int(self.hist_counts[i])
            if c > 0 and cumulative + c >= target:
                frac = (target - cumulative) / c
                value = edges[i] + frac * (edges[i + 1] - edges[i])
                return min(max(value, self.min), self.max)
            cumulative += c
        return self.max
