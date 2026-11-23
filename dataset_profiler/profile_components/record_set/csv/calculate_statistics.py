"""Column statistics, type rules and samples, streamed over chunks of a column.

The rules and constants here are shared with croissant-laminate (handoff 12c
§2), so both producers give the same values and types for the same column. Keep
the names and values in step with laminate's ``statistics.py``.

- Counts, mean, variance, standard deviation, min, max, range and the histogram
  are exact. Variance merges per-chunk moments with Chan's parallel formula, so
  it stays exact when the mean is large compared with the spread.
- Median and the 5th/95th percentiles are exact while a file holds at most
  ``EXACT_VALUES_PER_FILE`` numeric values in total. Above that budget every
  numeric column of the file switches to a t-digest (``fastdigest``), fed in
  file order. :attr:`_ColumnAccumulator.approximate` says when that happened.
- ``uniqueCount`` counts 64-bit hashes of the values within a per-file budget of
  ``UNIQUE_HASHES_PER_FILE`` hashes. A column that doesn't fit gets ``None``
  (written as ``"uniqueCount": null``), never a lower bound.
- Samples come from a reservoir seeded from the file's content hash and the
  column's name, so the same file always gives the same sample.
- Column types come from the raw strings (:class:`TypeClassifier`): the first
  of bool, int, float, date, datetime that every non-missing value matches,
  otherwise text.
"""

import hashlib
import math
import os
import re
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import pandas.api.types as ptypes

# No fallback sketch: without fastdigest the profiler must fail at start-up
# rather than silently report different quantiles from laminate.
from fastdigest import TDigest

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics

# Equal-width bins of the reported histogram.
HISTOGRAM_BINS = 10
# Values kept per column for the profile's ``sample``.
SAMPLE_SIZE = 10
# Numeric values buffered for exact quantiles, across all columns of one file.
EXACT_VALUES_PER_FILE = 20_000_000
# Value hashes kept for unique counts, across all columns of one file.
UNIQUE_HASHES_PER_FILE = 10_000_000
# A column's pending hashes are de-duplicated once they reach this many.
UNIQUE_COMPACT_AT = 1_000_000
# Size of the t-digest used above the exact budget.
TDIGEST_MAX_CENTROIDS = 1000

# A raw value is missing if it is one of these (pandas' default NA strings,
# spelled out so the rule doesn't depend on a pandas version).
NA_TOKENS = frozenset({
    "", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan", "1.#IND", "1.#QNAN",
    "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null",
})

# Type classes of raw (string) values, in order of precedence.
_TYPE_PATTERNS = {
    "bool": re.compile(r"(?i)^(true|false)$"),
    "int": re.compile(r"^[+-]?(0|[1-9]\d*)$"),
    "float": re.compile(r"^[+-]?((0|[1-9]\d*)(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "datetime": re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"),
}
TYPE_ORDER = tuple(_TYPE_PATTERNS)
# The same patterns over many values joined by a separator, so a whole batch is
# checked by one regex call. No pattern matches the separator.
_SEPARATOR = "\x1f"
# Groups are made non-capturing: capturing inside a repeated group is about
# twice as slow in Python's re engine.
_BATCH_PATTERNS = {
    kind: re.compile(rf"(?:{core})(?:{_SEPARATOR}(?:{core}))*", pattern.flags)
    for kind, pattern in _TYPE_PATTERNS.items()
    for core in [re.sub(r"\((?!\?)", "(?:", pattern.pattern.replace("(?i)", "").removeprefix("^").removesuffix("$"))]
}
# A value of the key's class always matches the value's class too.
_IMPLIES = {"int": "float"}
DATA_TYPES = {
    "bool": "sc:Boolean",
    "int": "sc:Integer",
    "float": "sc:Float",
    "date": "sc:Date",
    "datetime": "sc:DateTime",
    None: "sc:Text",
}
ISO_DATE = _TYPE_PATTERNS["date"]
ISO_DATETIME = _TYPE_PATTERNS["datetime"]

NUMERIC, BOOLEAN, TEXT = "numeric", "boolean", "text"


def timestamp() -> str:
    """The time statistics are stamped with: ``SOURCE_DATE_EPOCH`` when set, else now (UTC)."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else datetime.now(timezone.utc)
    return when.isoformat()


def sample_seed(file_sha256: str, column: str) -> int:
    """Seed of a column's sample: the file's content hash and the column's name."""
    digest = hashlib.sha256(f"{file_sha256}\0{column}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def kind_family(kind: Optional[str]) -> str:
    """The accumulator family of a type class: numeric, boolean or text."""
    if kind in ("int", "float"):
        return NUMERIC
    if kind == "bool":
        return BOOLEAN
    return TEXT


# -- types of raw values -----------------------------------------------------------

class TypeClassifier:
    """The type of a column of raw strings: the first class every value matches."""

    __slots__ = ("remaining", "seen")

    def __init__(self):
        self.remaining = TYPE_ORDER
        self.seen = 0

    def add(self, raw: str):
        """Classify one non-missing raw value."""
        self.seen += 1
        if self.remaining:
            # fullmatch, not match: "$" would also accept a trailing newline.
            self.remaining = tuple(t for t in self.remaining if _BATCH_PATTERNS[t].fullmatch(raw))

    def add_many(self, values: list):
        """Classify many non-missing raw values at once (the same result as :meth:`add` on each)."""
        if not values:
            return
        if not self.remaining:
            self.seen += len(values)
            return
        joined = _SEPARATOR.join(values)
        if joined.count(_SEPARATOR) != len(values) - 1:
            # A value holds the separator itself: classify one by one.
            for value in values:
                self.add(value)
            return
        self.seen += len(values)
        kept, implied = [], set()
        for kind in self.remaining:
            if kind in implied or _BATCH_PATTERNS[kind].fullmatch(joined):
                kept.append(kind)
                if kind in _IMPLIES:
                    implied.add(_IMPLIES[kind])
        self.remaining = tuple(kept)

    @property
    def kind(self) -> Optional[str]:
        """``bool``, ``int``, ``float``, ``date``, ``datetime``, or None for text."""
        return self.remaining[0] if self.seen and self.remaining else None


def convert(raw: Optional[str], kind: Optional[str]):
    """A raw value as the JSON value of its column's type."""
    if raw is None or raw in NA_TOKENS:
        return None
    if kind == "bool":
        return raw.lower() == "true"
    if kind == "int":
        return int(raw)
    if kind == "float":
        value = float(raw)
        return value if math.isfinite(value) else None
    return raw


# -- samples -------------------------------------------------------------------------

class Reservoir:
    """A uniform sample of ``k`` values from a stream (Algorithm L), seeded.

    The same seed and the same stream always give the same sample.
    """

    def __init__(self, seed: int, k: int = SAMPLE_SIZE):
        self.k = k
        self.items: list = []
        self.n = 0
        self._rng = np.random.Generator(np.random.PCG64(seed))
        self._w = 1.0
        self._next = None

    def _draw(self) -> float:
        return 1.0 - self._rng.random()   # in (0, 1], safe for log

    def _schedule(self, after: int):
        self._w *= math.exp(math.log(self._draw()) / self.k)
        if self._w >= 1.0:   # only reachable through underflow; replace the next value
            self._next = after + 1
            return
        self._next = after + int(math.floor(math.log(self._draw()) / math.log(1.0 - self._w))) + 1

    def add(self, value):
        n = self.n
        self.n += 1
        if n < self.k:
            self.items.append(value)
            if self.n == self.k:
                self._schedule(n)
        elif n == self._next:
            self.items[int(self._rng.integers(self.k))] = value
            self._schedule(n)

    def add_many(self, values):
        i, m = 0, len(values)
        while i < m and self.n < self.k:
            self.add(values[i])
            i += 1
        while i < m:
            jump = self._next - self.n
            if i + jump >= m:
                self.n += m - i
                return
            i += jump
            self.n += jump
            self.add(values[i])
            i += 1


# -- budgets -------------------------------------------------------------------------

class FileBudget:
    """Memory shared by all columns of one file: exact-quantile values and unique hashes."""

    def __init__(self):
        self.exact_left = EXACT_VALUES_PER_FILE
        self.unique_left = UNIQUE_HASHES_PER_FILE
        self.sketched = False
        self._members: list = []

    def register(self, accumulator: "_ColumnAccumulator"):
        self._members.append(accumulator)

    def compact_all(self):
        for member in self._members:
            member._compact()

    def take_exact(self, n: int) -> bool:
        """Reserve ``n`` buffered values, or switch every column of the file to its sketch."""
        if self.sketched:
            return False
        if n <= self.exact_left:
            self.exact_left -= n
            return True
        self.sketched = True
        for member in self._members:
            member._switch_to_sketch()
        return False


# -- the accumulator -----------------------------------------------------------------

def _to_python(value):
    """A numpy/pandas scalar as a JSON-serialisable Python value."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


def _hashes(values: np.ndarray) -> np.ndarray:
    return pd.util.hash_array(values)


def _text_hashes(values: np.ndarray) -> np.ndarray:
    """Hashes of text values, kept as Python strings.

    Never ``astype(str)``: that makes a fixed-width array sized by the longest
    value, which for long text runs to gigabytes.
    """
    if not all(isinstance(v, str) for v in values):
        values = np.array([str(v) for v in values], dtype=object)
    return pd.util.hash_array(values)


def _family_of_series(series: pd.Series) -> str:
    if ptypes.is_bool_dtype(series):
        return BOOLEAN
    if ptypes.is_numeric_dtype(series):
        return NUMERIC
    return TEXT


class _ColumnAccumulator:
    """Accumulates one column's statistics across streamed chunks.

    ``kind`` is ``numeric``, ``boolean`` or ``text``; left as None it is taken
    from the dtype of the first non-empty chunk. Pass one (:meth:`update`)
    gathers counts, moments, min/max, quantile values and unique hashes; pass
    two (:meth:`update_histogram`) bins numeric values once the global min/max
    are known. Boolean values may arrive as booleans or as ``true``/``false``
    strings; they are counted as 1 and 0.

    ``budget`` is shared by all columns of one file; each accumulator made
    without one gets its own.
    """

    def __init__(self, kind: Optional[str] = None, budget: Optional[FileBudget] = None):
        self.kind = kind
        self.budget = budget or FileBudget()
        self.budget.register(self)
        self.total = 0          # rows seen, missing included
        self.missing = 0
        self.count = 0          # non-missing values
        self.integer = True     # every numeric value was an integer
        # Chan's parallel moments.
        self._mean = 0.0
        self._m2 = 0.0
        self.ones = 0           # booleans: values that were true
        self.min = None
        self.max = None
        # Exact quantiles, or the sketch once the file's budget is spent.
        self._buffer: list = []
        self._digest: Optional[TDigest] = None
        # Unique counting.
        self._unique = np.empty(0, dtype=np.uint64)
        self._pending: list = []
        self._pending_n = 0
        self.unique_dropped = False
        # Histogram.
        self._edges = None
        self.hist_counts = np.zeros(HISTOGRAM_BINS, dtype=np.int64)

    # -- pass one -------------------------------------------------------------
    def update(self, series: pd.Series):
        n = len(series)
        if n == 0:
            return
        if self.kind is None:
            self.kind = _family_of_series(series)
        self.total += n
        if self.kind == TEXT:
            na_mask = series.isna().to_numpy()
            non_na = series.to_numpy(dtype=object)[~na_mask]
            self.missing += int(na_mask.sum())
            self.count += len(non_na)
            if len(non_na):
                self._add_hashes(_text_hashes(non_na))
            return

        if self.integer and not (ptypes.is_integer_dtype(series) or ptypes.is_bool_dtype(series)):
            self.integer = False
        values = self._as_float(series)
        finite = ~np.isnan(values)
        self.missing += int(n - finite.sum())
        values = values[finite]
        if values.size == 0:
            return
        self.count += int(values.size)
        if self.kind == BOOLEAN:
            self.ones += int(values.sum())

        # Chan's merge of this chunk's moments into the running ones.
        n_a, n_b = self.count - values.size, values.size
        mean_b = float(values.mean())
        m2_b = float(np.square(values - mean_b).sum())
        delta = mean_b - self._mean
        total = n_a + n_b
        self._mean += delta * n_b / total
        self._m2 += m2_b + delta * delta * n_a * n_b / total

        cmin, cmax = float(values.min()), float(values.max())
        self.min = cmin if self.min is None else min(self.min, cmin)
        self.max = cmax if self.max is None else max(self.max, cmax)

        if self.kind == NUMERIC:
            if self._digest is not None:
                self._digest.batch_update(values)
            elif self.budget.take_exact(values.size):
                self._buffer.append(values)
            else:
                self._digest.batch_update(values)
        self._add_hashes(_hashes(values))

    def _as_float(self, series: pd.Series) -> np.ndarray:
        if self.kind == BOOLEAN and not ptypes.is_bool_dtype(series) and not ptypes.is_numeric_dtype(series):
            lowered = series.astype("string").str.lower()
            out = np.where(lowered.isna(), np.nan, (lowered == "true").astype(float))
            return out.astype("float64")
        if ptypes.is_bool_dtype(series):
            return series.astype("float64").to_numpy()
        if ptypes.is_numeric_dtype(series):
            return series.to_numpy(dtype="float64", na_value=np.nan)
        return pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)

    def _switch_to_sketch(self):
        if self.kind != NUMERIC or self._digest is not None:
            return
        self._digest = TDigest(max_centroids=TDIGEST_MAX_CENTROIDS)
        if self._buffer:
            self._digest.batch_update(np.concatenate(self._buffer))
        self._buffer = []

    def _add_hashes(self, hashes: np.ndarray):
        if self.unique_dropped:
            return
        # De-duplicate the batch first: a chunk of a low-cardinality column
        # would otherwise count every row against the budget and be dropped
        # although its distinct values fit easily.
        hashes = np.unique(hashes)
        k = hashes.size
        if k > self.budget.unique_left:
            # Pending hashes still hold duplicates: de-duplicate every column of
            # the file before deciding that this one doesn't fit.
            self.budget.compact_all()
        if k > self.budget.unique_left:
            # This column's distinct values don't fit: no count rather than a wrong one.
            self.budget.unique_left += self._unique.size + self._pending_n
            self._unique = np.empty(0, dtype=np.uint64)
            self._pending, self._pending_n = [], 0
            self.unique_dropped = True
            return
        self.budget.unique_left -= k
        self._pending.append(hashes)
        self._pending_n += k
        if self._pending_n >= UNIQUE_COMPACT_AT:
            self._compact()

    def _compact(self):
        if not self._pending:
            return
        before = self._unique.size + self._pending_n
        self._unique = np.unique(np.concatenate([self._unique, *self._pending]))
        self._pending, self._pending_n = [], 0
        self.budget.unique_left += before - self._unique.size

    # -- pass two -------------------------------------------------------------
    def needs_histogram(self) -> bool:
        return self.kind in (NUMERIC, BOOLEAN) and self.count > 0 and self.min is not None

    def update_histogram(self, series: pd.Series):
        values = self._as_float(series)
        values = values[~np.isnan(values)]
        if values.size == 0:
            return
        codes = np.searchsorted(self.histogram_edges(), values, side="left") - 1
        # Bins are (low, high]; the first edge sits just below the minimum.
        codes = np.clip(codes, 0, HISTOGRAM_BINS - 1)
        self.hist_counts += np.bincount(codes, minlength=HISTOGRAM_BINS)[:HISTOGRAM_BINS]

    def histogram_edges(self) -> np.ndarray:
        if self._edges is None:
            mn, mx = self.min, self.max
            if mn == mx:
                # Mirror pd.cut's handling of a degenerate range.
                adj = 0.001 * abs(mn) if mn != 0 else 0.001
                self._edges = np.linspace(mn - adj, mx + adj, HISTOGRAM_BINS + 1)
            else:
                edges = np.linspace(mn, mx, HISTOGRAM_BINS + 1)
                # pd.cut nudges the first edge outward so the minimum is included.
                edges[0] -= (mx - mn) * 0.001
                self._edges = edges
        return self._edges

    # -- finalisation ---------------------------------------------------------
    @property
    def approximate(self) -> bool:
        """True when the quantiles come from the t-digest, not from every value."""
        return self._digest is not None

    def unique_count(self) -> Optional[int]:
        if self.unique_dropped:
            return None
        self._compact()
        return int(self._unique.size)

    def numeric_data_type(self) -> str:
        """The data type of a numeric or boolean column, from the dtypes pandas read."""
        if self.kind == BOOLEAN:
            return "sc:Boolean"
        return "sc:Integer" if self.integer else "sc:Float"

    # Kept for callers of the former API (the JSON record set).
    data_type = numeric_data_type

    def _quantiles(self):
        if self.kind == BOOLEAN:
            # The majority value; a tie gives false.
            return (1.0 if self.ones > self.count - self.ones else 0.0), None, None
        if self._digest is not None:
            return (float(self._digest.quantile(0.5)), float(self._digest.quantile(0.05)),
                    float(self._digest.quantile(0.95)))
        values = np.concatenate(self._buffer)
        p05, median, p95 = np.quantile(values, [0.05, 0.5, 0.95], method="linear")
        return float(median), float(p05), float(p95)

    def build_statistics(self) -> ColumnStatistics:
        if self.total == 0:
            return ColumnStatistics()
        missing_pct = float(self.missing / self.total * 100)

        if self.kind == TEXT:
            return ColumnStatistics(
                row_count=self.count,
                missing_count=self.missing,
                missing_percentage=missing_pct,
                unique_count=self.unique_count(),
            )

        if self.count == 0:
            return ColumnStatistics(
                row_count=0,
                missing_count=self.missing,
                missing_percentage=missing_pct,
                histogram=[],
                unique_count=0,
            )

        if self.count > 1:
            variance = self._m2 / (self.count - 1)
            std = math.sqrt(variance)
        else:
            variance = std = float("nan")   # as pandas, for a single value
        median, p05, p95 = self._quantiles()

        return ColumnStatistics(
            row_count=self.count,
            mean=float(self._mean),
            median=median,
            standard_deviation=float(std),
            min_value=float(self.min),
            max_value=float(self.max),
            missing_count=self.missing,
            missing_percentage=missing_pct,
            histogram=self._histogram_list(),
            unique_count=self.unique_count(),
            variance=float(variance),
            range_value=float(self.max - self.min),
            percentile05=p05,
            percentile95=p95,
            generated_at=timestamp(),
        )

    def _histogram_list(self) -> list:
        edges = self.histogram_edges()
        return [
            {"binRange": [float(edges[i]), float(edges[i + 1])], "count": int(self.hist_counts[i])}
            for i in range(HISTOGRAM_BINS)
        ]
