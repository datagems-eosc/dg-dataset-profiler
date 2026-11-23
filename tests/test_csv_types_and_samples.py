"""CSV types, samples and malformed rows (handoff 12c P4, P5, P10)."""

import json

import pytest

from dataset_profiler.profile_components.record_set.csv.csv_record_set import CSVRecordSet, string_pass


def profile(tmp_path, text, name="data.csv"):
    (tmp_path / name).write_text(text)
    return CSVRecordSet(str(tmp_path), name, "file-id")


def fields(record_set):
    return {f.name: f for f in record_set.fields}


def column_csv(name, values):
    return name + "\n" + "".join(f"{v}\n" for v in values)


@pytest.mark.parametrize("values, expected", [
    (["01234", "00012"], "sc:Text"),
    (["1.0", "2.0", "", "4.0"], "sc:Float"),
    (["1", "2", "", "4"], "sc:Integer"),
    (["0", "1", "1"], "sc:Integer"),
    (["true", "FALSE", ""], "sc:Boolean"),
    (["1", "2.5"], "sc:Float"),
    (["2024-01-02", "2024-02-03"], "sc:Date"),
    (["2024-01-02T10:00:00Z", "2024-01-02 11:30"], "sc:DateTime"),
    (["", "NA", "null"], "sc:Text"),
])
def test_type_decision(tmp_path, values, expected):
    record_set = profile(tmp_path, column_csv("x", values))
    assert record_set.fields[0].dataType == expected


def test_mixed_column_is_text_whatever_rows_are_drawn(tmp_path):
    values = [str(i) for i in range(395)] + ["word"] * 5
    record_set = profile(tmp_path, column_csv("x", values))
    field = record_set.fields[0]
    assert field.dataType == "sc:Text"
    # Text columns carry text statistics only; the numeric keys stay, as null.
    statistics = field.to_dict()["statistics"]
    assert statistics["mean"] is None and statistics["histogram"] is None
    assert statistics["uniqueCount"] == 396


def test_leading_zero_column_keeps_strings(tmp_path):
    record_set = profile(tmp_path, column_csv("zip", ["01234", "00012", "01234"]))
    field = record_set.fields[0]
    assert field.dataType == "sc:Text"
    assert sorted(field.sample) == ["00012", "01234", "01234"]
    statistics = field.to_dict()["statistics"]
    assert statistics["mean"] is None and statistics["median"] is None
    assert statistics["uniqueCount"] == 2


def test_samples_are_converted_to_the_column_type(tmp_path):
    record_set = profile(tmp_path, "i,f,b,t\n1,1.5,true,a\n2,,false,b\n,3.0,,c\n")
    by_name = fields(record_set)
    assert sorted(by_name["i"].sample) == [1, 2]
    assert all(isinstance(v, int) for v in by_name["i"].sample)
    assert sorted(by_name["f"].sample) == [1.5, 3.0]
    assert sorted(by_name["b"].sample) == [False, True]
    assert sorted(by_name["t"].sample) == ["a", "b", "c"]


def test_boolean_column_statistics(tmp_path):
    record_set = profile(tmp_path, column_csv("active", ["true", "false", "true", "true"]))
    field = record_set.fields[0]
    assert field.dataType == "sc:Boolean"
    statistics = field.to_dict()["statistics"]
    assert statistics["mean"] == 0.75
    assert statistics["median"] == 1
    assert statistics["percentile05"] is None and statistics["percentile95"] is None
    assert sum(b["count"] for b in json.loads(statistics["histogram"])) == 4


def _without_volatile(record_set):
    out = []
    for f in record_set.fields:
        d = f.to_dict()
        d.pop("@id")
        d["statistics"].pop("@id")
        d["statistics"].pop("generatedAt")
        out.append(d)
    return out


def test_two_runs_are_identical(tmp_path):
    rows = "".join(f"{i},{i * 0.5},name{i % 17},{'true' if i % 2 else 'false'}\n" for i in range(5000))
    (tmp_path / "data.csv").write_text("a,b,c,d\n" + rows)
    first = CSVRecordSet(str(tmp_path), "data.csv", "file-id")
    second = CSVRecordSet(str(tmp_path), "data.csv", "file-id")
    assert _without_volatile(first) == _without_volatile(second)
    assert all(len(f.sample) == 10 for f in first.fields)


def test_sample_seed_follows_the_content_hash(tmp_path):
    rows = "".join(f"{i}\n" for i in range(5000))
    (tmp_path / "data.csv").write_text("a\n" + rows)
    one = CSVRecordSet(str(tmp_path), "data.csv", "file-id", file_sha256="a" * 64)
    other = CSVRecordSet(str(tmp_path), "data.csv", "file-id", file_sha256="b" * 64)
    assert one.fields[0].sample != other.fields[0].sample


# -- P10: malformed rows ----------------------------------------------------------

def test_malformed_rows_are_counted(tmp_path):
    record_set = profile(tmp_path, "a,b\n1,x\n2,y\n1,2,3,4\n9\n3,z\n")
    report = record_set.report
    assert (report["skipped_rows"], report["skipped_lines"]) == (1, [4])
    assert (report["padded_rows"], report["padded_lines"]) == (1, [5])
    # pandas agrees: the long row is dropped, the short one kept.
    assert fields(record_set)["a"].statistics.row_count == 4


def test_blank_lines_are_ignored(tmp_path):
    record_set = profile(tmp_path, "a,b\n1,x\n\n2,y\n")
    assert record_set.report["skipped_rows"] == 0
    assert record_set.report["padded_rows"] == 0
    assert record_set.report["rows"] == 2


def test_line_numbers_are_physical_with_quoted_newlines(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text('a,b\n1,"two\nlines"\n2,y,extra\n3\n')
    result = string_pass(str(path), "utf-8", ",", "", ["a", "b"])
    assert result.skipped_lines == [4]
    assert result.padded_lines == [5]
