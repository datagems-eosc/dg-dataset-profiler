"""Checksums, file set includes and Excel sheet names (handoff 12c P6, P7, P8)."""

import hashlib

import pandas as pd
import pytest

from dataset_profiler.profile_components.distribution import (
    get_distribution_of_file_object,
    get_distribution_of_file_set,
)
from dataset_profiler.profile_components.record_set.csv import csv_record_set
from dataset_profiler.profile_components.record_set.csv.csv_record_set import get_record_sets_from_excel


# -- P6: sha256 of the content ------------------------------------------------------

def test_sha256_is_the_content_hash(tmp_path):
    path = tmp_path / "a.csv"
    path.write_bytes(b"x,y\n1,2\n")
    distribution = get_distribution_of_file_object(str(path), "id")
    assert distribution.sha256_check == hashlib.sha256(b"x,y\n1,2\n").hexdigest()
    assert distribution.sha256_check != hashlib.sha256(str(path).encode()).hexdigest()


def test_identical_content_gives_the_same_hash(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    big = b"0123456789" * 300_000   # spans several 1 MiB chunks
    (tmp_path / "one" / "a.bin").write_bytes(big)
    (tmp_path / "two" / "b.bin").write_bytes(big)
    first = get_distribution_of_file_object(str(tmp_path / "one" / "a.bin"), "1")
    second = get_distribution_of_file_object(str(tmp_path / "two" / "b.bin"), "2")
    assert first.sha256_check == second.sha256_check == hashlib.sha256(big).hexdigest()


# -- P7: FileSet includes -------------------------------------------------------------

def test_nested_file_set_includes_the_relative_path(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "x.txt").write_text("hi")
    distribution = get_distribution_of_file_set(str(nested), "id", relative_path="a/b")
    assert distribution.includes == "a/b/*"


@pytest.mark.parametrize("relative", ["b", "b/", "/b"])
def test_top_level_file_set_includes(tmp_path, relative):
    folder = tmp_path / "b"
    folder.mkdir()
    distribution = get_distribution_of_file_set(str(folder), "id", relative_path=relative)
    assert distribution.includes == "b/*"


def test_file_set_without_relative_path_keeps_the_folder_name(tmp_path):
    folder = tmp_path / "b"
    folder.mkdir()
    assert get_distribution_of_file_set(str(folder) + "/", "id").includes == "b/*"


# -- P8: Excel sheet names ------------------------------------------------------------

@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"answer": ["yes", "no"]}).to_excel(writer, sheet_name="Responses", index=False)
        pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        pd.DataFrame({"n": [1, 2, 3]}).to_excel(writer, sheet_name="Numbers", index=False)
        pd.DataFrame({"m": [4, 5]}).to_excel(writer, sheet_name="Last", index=False)
    return path


def test_sheet_names_survive_a_skipped_empty_sheet(workbook):
    record_sets = get_record_sets_from_excel(str(workbook.parent), workbook.name, "wb")
    assert [rs.inject_distribution["name"] for rs in record_sets] == ["Responses", "Numbers", "Last"]
    assert [rs.name for rs in record_sets] == ["Responses", "Numbers", "Last"]
    assert all(rs.inject_distribution["containedIn"] == {"@id": "wb"} for rs in record_sets)


def test_sheet_names_survive_a_failing_sheet(workbook, monkeypatch):
    real = csv_record_set.CSVRecordSet

    def failing_on_numbers(*args, **kwargs):
        if kwargs["file_object"] == "Numbers.csv":
            raise pd.errors.ParserError("broken")
        return real(*args, **kwargs)

    monkeypatch.setattr(csv_record_set, "CSVRecordSet", failing_on_numbers)
    record_sets = get_record_sets_from_excel(str(workbook.parent), workbook.name, "wb")
    assert [rs.inject_distribution["name"] for rs in record_sets] == ["Responses", "Last"]
    assert [rs.fields[0].name for rs in record_sets] == ["answer", "m"]


def test_sheet_samples_are_seeded_per_sheet(tmp_path):
    path = tmp_path / "book.xlsx"
    frame = pd.DataFrame({"v": range(1000)})
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(writer, sheet_name="One", index=False)
        frame.to_excel(writer, sheet_name="Two", index=False)
    one, two = get_record_sets_from_excel(str(tmp_path), path.name, "wb")
    again = get_record_sets_from_excel(str(tmp_path), path.name, "wb")
    assert one.fields[0].sample != two.fields[0].sample
    assert [rs.fields[0].sample for rs in again] == [one.fields[0].sample, two.fields[0].sample]
