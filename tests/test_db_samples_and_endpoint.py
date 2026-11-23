"""Database samples and the recorded endpoint (handoff 12c P11, P17). No database needed."""

import json

import pytest

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.distribution import get_distribution_of_database_connection
from dataset_profiler.profile_components.record_set.db import database_connector
from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
    check_requested_endpoint,
)
from dataset_profiler.profile_components.record_set.db.db_record_set import DBColumnField, db_sample_text


# -- P11: samples of jsonb and arrays ---------------------------------------------------

def test_jsonb_and_array_samples_are_json():
    column = {"column": "payload", "data_type": "JSONB", "values": [{"k": 702}, ["a", "b"], {"é": [1, None]}]}
    field = DBColumnField(column, "table-id", {}, statistics=ColumnStatistics())
    assert [json.loads(v) for v in field.sample] == [{"k": 702}, ["a", "b"], {"é": [1, None]}]
    assert field.sample[2] == '{"é": [1, null]}'


def test_other_samples_keep_str():
    import datetime
    assert db_sample_text(5) == "5"
    assert db_sample_text("text") == "text"
    assert db_sample_text(datetime.date(2024, 1, 2)) == "2024-01-02"


def test_nested_non_json_values_fall_back_to_str():
    import datetime
    assert json.loads(db_sample_text({"when": datetime.date(2024, 1, 2)})) == {"when": "2024-01-02"}


# -- P17: requested vs used endpoint -----------------------------------------------------

@pytest.fixture
def endpoints(monkeypatch):
    monkeypatch.setenv("DATAGEMS_POSTGRES_HOST", "172.16.68.5")
    monkeypatch.setenv("DATAGEMS_POSTGRES_PORT", "30432")
    monkeypatch.setenv("DATAGEMS_TIMESCALE_DB_HOST", "172.16.68.5")
    monkeypatch.setenv("DATAGEMS_TIMESCALE_DB_PORT", "30433")


@pytest.fixture
def warnings(monkeypatch):
    seen = []

    class Recorder:
        def warning(self, message, **kwargs):
            seen.append((message, kwargs))

    monkeypatch.setattr(database_connector, "profiler_logger", Recorder())
    return seen


def test_same_endpoint_gives_no_warning(endpoints, warnings):
    assert check_requested_endpoint("PostgreSQL", "db", "172.16.68.5", 30432, "ds") is None
    assert check_requested_endpoint("TimescaleDB", "db", "172.16.68.5", "30433", "ds") is None
    assert warnings == []


def test_different_host_warns_once_and_keeps_the_content_url(endpoints, warnings):
    message = check_requested_endpoint("TimescaleDB", "ds_weather_stream", "172.16.59.5", 30433, "ds-1")
    assert message is not None
    assert "172.16.59.5:30433" in message and "172.16.68.5:30433" in message
    assert "ds_weather_stream" in message and "ds-1" in message
    assert len(warnings) == 1
    assert warnings[0][1]["requested_endpoint"] == "172.16.59.5:30433"
    assert warnings[0][1]["used_endpoint"] == "172.16.68.5:30433"
    assert warnings[0][1]["dataset_id"] == "ds-1"

    connection = get_distribution_of_database_connection(
        "conn", "ds_weather_stream", "postgresql", "TimescaleDB", "172.16.59.5", 30433)
    assert connection.to_dict()["contentUrl"] == "postgresql://172.16.59.5:30433/ds_weather_stream"


def test_different_port_warns(endpoints, warnings):
    assert check_requested_endpoint("PostgreSQL", "db", "172.16.68.5", 5432) is not None
    assert len(warnings) == 1


def test_each_engine_uses_its_own_env_pair(endpoints, warnings):
    # The Timescale port is wrong for PostgreSQL and the other way round.
    assert check_requested_endpoint("PostgreSQL", "db", "172.16.68.5", 30433) is not None
    assert check_requested_endpoint("TimescaleDB", "db", "172.16.68.5", 30432) is not None
    assert check_requested_endpoint("PostgreSQL", "db", "172.16.68.5", 30432) is None
    assert len(warnings) == 2


def test_connector_connects_with_its_own_settings(endpoints, monkeypatch):
    monkeypatch.setenv("DATAGEMS_TIMESCALE_DB_USERNAME", "u")
    monkeypatch.setenv("DATAGEMS_TIMESCALE_DB_PASSWORD", "p")
    db = DatagemsPostgres("ds", "public", "TimescaleDB")
    assert db.connection_uri == "postgresql+psycopg2://u:p@172.16.68.5:30433/ds"


def test_unsupported_engine_still_raises():
    with pytest.raises(ValueError):
        DatagemsPostgres("ds", "public", "MySQL")
    assert check_requested_endpoint("MySQL", "ds", "h", 1) is None
