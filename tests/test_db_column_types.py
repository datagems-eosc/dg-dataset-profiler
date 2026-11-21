"""Database column types map to the same schema.org types as file columns."""

import pytest

from dataset_profiler.utilities import find_column_type_in_db


@pytest.mark.parametrize("db_type, expected", [
    ("SMALLINT", "sc:Integer"),
    ("INTEGER", "sc:Integer"),
    ("BIGINT", "sc:Integer"),
    ("REAL", "sc:Float"),
    ("DOUBLE PRECISION", "sc:Float"),  # was a sequence pattern that never matched
    ("NUMERIC", "sc:Float"),
    ("BOOLEAN", "sc:Boolean"),
    ("DATE", "sc:Date"),
    ("TIMESTAMP WITHOUT TIME ZONE", "sc:DateTime"),
    ("TIMESTAMP WITH TIME ZONE", "sc:DateTime"),
    ("TEXT", "sc:Text"),
    ("VARCHAR", "sc:Text"),  # get_types_of_db renames "character varying"
    ("CHARACTER", "sc:Text"),
    ("double precision", "sc:Float"),
])
def test_known_types(db_type, expected):
    assert find_column_type_in_db(db_type) == expected


@pytest.mark.parametrize("db_type", ["ARRAY", "USER-DEFINED", "", None])
def test_types_without_a_counterpart_map_to_none(db_type):
    assert find_column_type_in_db(db_type) is None
