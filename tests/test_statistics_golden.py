"""Golden values of the column statistics (handoff 12c P1, P2, P3).

The rules are shared with croissant-laminate; see calculate_statistics.py.
"""

import numpy as np
import pandas as pd
import pytest

from dataset_profiler.profile_components.record_set.csv import calculate_statistics as cs
from dataset_profiler.profile_components.record_set.csv.calculate_statistics import (
    BOOLEAN,
    NUMERIC,
    FileBudget,
    _ColumnAccumulator,
)
from dataset_profiler.profile_components.record_set.csv.csv_record_set import CSVRecordSet


def stats(values, kind=None, chunk=None):
    acc = _ColumnAccumulator(kind)
    series = pd.Series(values)
    chunks = [series] if chunk is None else [series[i:i + chunk] for i in range(0, len(series), chunk)]
    for part in chunks:
        acc.update(part)
    if acc.needs_histogram():
        for part in chunks:
            acc.update_histogram(part)
    return acc, acc.build_statistics()


# -- P1: quantiles --------------------------------------------------------------

def test_skewed_median_is_exact():
    _, s = stats([1] * 990 + [1_000_000] * 10)
    assert s.median == 1
    assert s.percentile95 == 1


def test_two_values_median_interpolates():
    _, s = stats([1, 4])
    assert s.median == 2.5


def test_lognormal_quantiles_match_numpy():
    values = np.random.default_rng(7).lognormal(size=1_000_000)
    _, s = stats(values, chunk=100_000)
    p05, median, p95 = np.quantile(values, [0.05, 0.5, 0.95], method="linear")
    assert s.median == pytest.approx(median, abs=1e-12)
    assert s.percentile05 == pytest.approx(p05, abs=1e-12)
    assert s.percentile95 == pytest.approx(p95, abs=1e-12)


def test_boolean_median_tie_gives_false():
    acc, s = stats([True] * 3 + [False] * 3)
    assert acc.kind == BOOLEAN
    assert s.median == 0
    assert s.percentile05 is None and s.percentile95 is None
    assert s.mean == 0.5 and s.min_value == 0 and s.max_value == 1


def test_boolean_median_is_majority():
    _, s = stats([True] * 4 + [False] * 3)
    assert s.median == 1


def _sketched(values):
    budget = FileBudget()
    acc = _ColumnAccumulator(NUMERIC, budget)
    for i in range(0, len(values), 10_000):
        acc.update(pd.Series(values[i:i + 10_000]))
    return acc, acc.build_statistics()


def test_over_budget_switches_to_tdigest_within_half_a_rank_point(monkeypatch):
    monkeypatch.setattr(cs, "EXACT_VALUES_PER_FILE", 1000)
    values = np.random.default_rng(11).lognormal(size=200_000)
    acc, s = _sketched(values)
    assert acc.approximate
    ordered = np.sort(values)
    for estimate, q in ((s.median, 0.5), (s.percentile95, 0.95)):
        rank = np.searchsorted(ordered, estimate) / len(values)
        assert abs(rank - q) <= 0.005


def test_sketch_is_reproducible(monkeypatch):
    monkeypatch.setattr(cs, "EXACT_VALUES_PER_FILE", 1000)
    values = np.random.default_rng(11).lognormal(size=200_000)
    first, second = _sketched(values)[1], _sketched(values)[1]
    assert (first.median, first.percentile05, first.percentile95) == (
        second.median, second.percentile05, second.percentile95)


def test_budget_is_shared_by_every_numeric_column_of_a_file(monkeypatch):
    monkeypatch.setattr(cs, "EXACT_VALUES_PER_FILE", 1000)
    budget = FileBudget()
    small = _ColumnAccumulator(NUMERIC, budget)
    big = _ColumnAccumulator(NUMERIC, budget)
    small.update(pd.Series(np.arange(10.0)))
    assert not small.approximate
    big.update(pd.Series(np.arange(5000.0)))
    # The whole file switched, the small column included.
    assert small.approximate and big.approximate


# -- P2: variance ---------------------------------------------------------------

@pytest.mark.parametrize("values", [
    [1e9 + 1, 1e9 + 2, 1e9 + 3],
    list(1e12 + np.arange(2000.0)),
])
def test_variance_is_stable_for_large_means(values):
    _, s = stats(values, chunk=700)
    expected = np.var(values, ddof=1)
    assert s.variance == pytest.approx(expected, rel=1e-9)
    assert s.standard_deviation == pytest.approx(np.sqrt(expected), rel=1e-9)


def test_variance_of_one_value_is_nan():
    _, s = stats([5.0])
    assert np.isnan(s.variance)


# -- P3: uniqueCount ------------------------------------------------------------

def test_unique_count_is_exact_beyond_the_old_cap():
    _, s = stats(np.arange(200_000), chunk=50_000)
    assert s.unique_count == 200_000


def test_duplicates_across_chunks_are_counted_once():
    _, s = stats(np.tile(np.arange(1000), 50), chunk=7_000)
    assert s.unique_count == 1000


def test_text_unique_count():
    _, s = stats(["a", "b", "a", None, "c"])
    assert s.unique_count == 3
    assert s.missing_count == 1


def test_over_unique_budget_writes_null_and_keeps_the_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "UNIQUE_HASHES_PER_FILE", 1000)
    path = tmp_path / "ids.csv"
    path.write_text("id,group\n" + "".join(f"{i},{i % 3}\n" for i in range(5000)))
    record_set = CSVRecordSet(str(tmp_path), "ids.csv", "file-id")
    by_name = {f.name: f.to_dict()["statistics"] for f in record_set.fields}
    assert "uniqueCount" in by_name["id"]
    assert by_name["id"]["uniqueCount"] is None
    assert by_name["group"]["uniqueCount"] == 3
    assert record_set.report["unique_count_dropped"] == ["id"]


def test_csv_unique_count_counts_every_chunk(monkeypatch, tmp_path):
    # Chunks of 1000 rows: the old code checked its cap only after each chunk.
    from dataset_profiler.profile_components.record_set.csv import csv_record_set
    monkeypatch.setattr(csv_record_set, "CHUNK_CELLS", 1000)
    path = tmp_path / "ids.csv"
    path.write_text("id\n" + "".join(f"{i}\n" for i in range(200_000)))
    record_set = CSVRecordSet(str(tmp_path), "ids.csv", "file-id")
    assert record_set.fields[0].statistics.unique_count == 200_000
