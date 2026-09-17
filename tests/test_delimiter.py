"""Delimiter detection for CSV record sets.

Both cases below were real: a semicolon file of Greek station names read as a
single column, and a comma file of ESCO URIs split on the letter "n".
"""

import pytest

from dataset_profiler.profile_components.record_set.csv.csv_record_set import (
    DELIMITER_SAMPLE_CHARS,
    CSVRecordSet,
)


def _detector(tmp_path, name, text, encoding="utf-8"):
    path = tmp_path / name
    path.write_text(text, encoding=encoding)
    # Only the delimiter logic is under test, so skip the full profiling run
    # that __init__ would trigger.
    rs = CSVRecordSet.__new__(CSVRecordSet)
    rs.distribution_path, rs.file_object, rs._encoding = str(tmp_path), name, None
    return rs, str(path)


def test_long_semicolon_rows_are_detected(tmp_path):
    """Long non-ASCII rows used to leave the 1KB sample ending mid-row."""
    # Thirteen columns, like the file that broke: rows long enough that only a
    # handful fit in the old 1KB sample. Shorter rows sniff fine even under the
    # old logic, so they would not guard this bug.
    header = ("reading_id;station_code;station_name;municipality;latitude;longitude;measured_at;"
              "pm2_5_ugm3;pm10_ugm3;no2_ugm3;o3_ugm3;temperature_c;relative_humidity_pct\n")
    row = ("{i};THE-KAL;Θεσσαλονίκη - Καλαμαριά;Thessaloniki;40.585;22.951;2025-03-01T{h:02d}:00:00;"
           "12.4;21.9;44.1;87.3;14.2;71\n")
    body = header + "".join(row.format(i=900000 + i, h=i % 24) for i in range(400))
    rs, path = _detector(tmp_path, "air.csv", "﻿" + body)
    assert rs._detect_delimiter(path) == ";"


def test_letters_are_never_chosen_as_delimiters(tmp_path):
    """The unrestricted Sniffer picked "n" for this ESCO file."""
    header = "originalSkillUri,originalSkillType,relationType,relatedSkillType,relatedSkillUri\n"
    row = ("http://data.europa.eu/esco/skill/{i:08d}-8fad-454b-90c7-ed858cc993f2,knowledge,"
           "optional,knowledge,http://data.europa.eu/esco/skill/d4a0744a-508b-4a5e-97a5-ad1fc7f55e6e\n")
    rs, path = _detector(tmp_path, "skills.csv", header + "".join(row.format(i=i) for i in range(50)))
    assert rs._detect_delimiter(path) == ","


@pytest.mark.parametrize("sep", [",", ";", "\t", "|"])
def test_each_supported_delimiter_is_detected(tmp_path, sep):
    lines = [sep.join(["id", "name", "value"])] + [sep.join([str(i), f"n{i}", "1.5"]) for i in range(20)]
    rs, path = _detector(tmp_path, "t.csv", "\n".join(lines) + "\n")
    assert rs._detect_delimiter(path) == sep


def test_small_file_keeps_its_last_row(tmp_path):
    """A file shorter than the sample is read whole; trimming would lose a real row."""
    rs, path = _detector(tmp_path, "tiny.csv", "a;b;c\n1;2;3")  # no trailing newline
    assert rs._detect_delimiter(path) == ";"


def test_sample_is_large_enough_to_cover_many_rows():
    assert DELIMITER_SAMPLE_CHARS >= 16 * 1024
