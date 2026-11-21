"""Database column statistics against the ERA5-Land database (needs the VPN)."""

import json

import pytest

from dataset_profiler.profile_components.record_set.db.db_calculate_statistics import (
    calculate_table_statistics, db_statistics_enabled,
)


@pytest.fixture(scope="module")
def era5():
    from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres
    try:
        db = DatagemsPostgres(database="ds_era5_land", schema="public", engine="PostgreSQL")
        with db.engine.connect():
            pass
    except Exception as e:  # no VPN, no credentials
        pytest.skip(f"ERA5-Land database not reachable: {e}")
    return db, db.get_types_of_db()


def test_statistics_are_opt_in(monkeypatch):
    monkeypatch.delenv("ENABLE_DB_STATISTICS", raising=False)
    assert not db_statistics_enabled()
    monkeypatch.setenv("ENABLE_DB_STATISTICS", "true")
    assert db_statistics_enabled()


def test_numeric_columns_count_every_row(era5):
    db, types = era5
    stats = calculate_table_statistics(db, "elevation_short", types["elevation_short"])
    elevation = stats["elevation"].to_dict()
    assert elevation["rowCount"] + elevation["missingCount"] == 138_158
    assert sum(b["count"] for b in json.loads(elevation["histogram"])) == elevation["rowCount"]
    assert elevation["min"] <= elevation["percentile05"] <= elevation["median"] <= elevation["percentile95"] <= elevation["max"]
    assert stats["id"].to_dict()["uniqueCount"] == 138_158


def test_text_columns_get_counts_only(era5):
    db, types = era5
    label = calculate_table_statistics(db, "landcover_type", types["landcover_type"])["level1_label"].to_dict()
    assert label["rowCount"] == 44
    assert label["uniqueCount"] == 5
    assert label["mean"] is None and label["histogram"] is None


def test_a_failure_gives_no_statistics(era5):
    db, _ = era5
    assert calculate_table_statistics(db, "no_such_table", {"x": "INTEGER"}) == {}
