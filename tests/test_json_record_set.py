"""JSON and JSON Lines record sets.

A JSON file is profiled as a table whose columns are JSONPaths, with the same
statistics as CSV columns. The cases here pin the decisions agreed with MoMa
and DMM: an absent key counts as missing exactly like ``null``, ``rowCount`` is
the number of non-null values, ``jsonTypes`` and ``topValues`` live on the
statistics, and the layout and nesting of the file are reported per record set.
"""

import json

import pytest

from dataset_profiler.profile_components.constants import REFERENCES_TEMPLATE
from dataset_profiler.profile_components.record_set.json import json_record_set
from dataset_profiler.profile_components.record_set.json.json_record_set import (
    ARRAY_OF_RECORDS,
    INVALID,
    JSON_LINES,
    SINGLE_DOCUMENT,
    WRAPPED_RECORDS,
    JSONRecordSet,
)
from dataset_profiler.profile_models import DatasetProfile


def _profile(tmp_path, content, name="data.json", raw=False):
    path = tmp_path / name
    if raw:
        path.write_bytes(content)
    else:
        path.write_text(content if isinstance(content, str) else json.dumps(content),
                        encoding="utf-8")
    return JSONRecordSet(str(path), "file-1", use_llm=False)


def _columns(record_set):
    return {c["name"]: c for c in record_set.to_dict_cdd()["columns"]}


# -- layouts -------------------------------------------------------------------------

def test_array_of_records(tmp_path):
    rs = _profile(tmp_path, [{"id": 1, "city": "Athens"}, {"id": 2, "city": "Patras"}])

    assert rs.structure.shape == ARRAY_OF_RECORDS
    assert rs.structure.record_path == "$[*]"
    assert rs.record_count == 2
    assert _columns(rs)["city"]["json_path"] == "$[*].city"


def test_wrapped_records_pick_the_outermost_array_not_the_largest(tmp_path):
    stations = [
        {"id": f"S{i}", "readings": [{"t": 20.0 + j} for j in range(10)]}
        for i in range(3)
    ]
    rs = _profile(tmp_path, {"meta": {"source": "NOA", "license": "CC BY 4.0"},
                             "stations": stations})

    # 30 readings outnumber 3 stations, but the stations are the records.
    assert rs.structure.shape == WRAPPED_RECORDS
    assert rs.structure.record_path == "$.stations[*]"
    assert rs.record_count == 3
    assert rs.structure.document_metadata == {
        "$.meta.source": "NOA", "$.meta.license": "CC BY 4.0",
    }
    assert _columns(rs)["readings[*].t"]["json_path"] == "$.stations[*].readings[*].t"


def test_json_lines_counts_broken_lines_without_failing(tmp_path):
    rs = _profile(tmp_path, '{"a": 1}\n{"a": 2}\nnot json\n\n{"a": 3}\n', name="e.jsonl")

    assert rs.structure.shape == JSON_LINES
    assert rs.record_count == 3
    assert rs.parse_errors == 1
    assert rs.to_dict_cdd()["original_format"] == "jsonl"


def test_json_file_that_is_really_json_lines(tmp_path):
    rs = _profile(tmp_path, '{"a": 1}\n{"a": 2}\n', name="events.json")

    assert rs.structure.shape == JSON_LINES
    assert rs.record_count == 2


def test_single_document(tmp_path):
    rs = _profile(tmp_path, {"title": "Config", "settings": {"depth": 3, "verbose": True}})

    assert rs.structure.shape == SINGLE_DOCUMENT
    assert rs.record_count == 1
    assert set(_columns(rs)) == {"title", "settings.depth", "settings.verbose"}


def test_invalid_json_gives_a_record_set_without_fields(tmp_path):
    rs = _profile(tmp_path, "this is not json")

    assert rs.structure.shape == INVALID
    assert rs.parse_errors == 1
    assert rs.fields == []
    assert rs.to_dict_cdd()["json_profile"]["parse_errors"] == 1


def test_file_broken_part_way_keeps_the_records_before_the_break(tmp_path):
    rs = _profile(tmp_path, '[{"a": 1}, {"a": 2}, {"a": ')

    assert rs.record_count == 2
    assert rs.parse_errors == 1


def test_geojson_dialect(tmp_path):
    rs = _profile(tmp_path, {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "A"}, "geometry": None},
    ]}, name="places.geojson")

    assert rs.structure.dialect == "geojson"
    assert rs.structure.record_path == "$.features[*]"


# -- statistics: same meaning as CSV --------------------------------------------------

def test_absent_and_null_both_count_as_missing(tmp_path):
    records = [{"op": "NOA"}, {"op": "NOA"}, {"op": "HNMS"}, {"op": None}, {}]
    stats = _columns(_profile(tmp_path, records))["op"]["statistics"]

    assert stats["rowCount"] == 3              # non-null values
    assert stats["missingCount"] == 2          # one null, one absent
    assert stats["missingPercentage"] == 40.0  # out of all 5 records
    assert stats["jsonTypes"] == {"string": 3}


def test_repeated_fields_count_over_array_elements(tmp_path):
    records = [
        {"readings": [{"t": 1.5}, {"t": 2.5}, {}]},
        {"readings": [{"t": None}]},
    ]
    column = _columns(_profile(tmp_path, records))["readings[*].t"]

    assert column["repeated"] is True
    assert column["statistics"]["rowCount"] == 2
    assert column["statistics"]["missingCount"] == 2     # out of 4 elements
    assert column["statistics"]["missingPercentage"] == 50.0
    assert column["array_length"] == {"min": 1, "avg": 2.0, "max": 3}


def test_mixed_types_keep_numeric_statistics_from_the_majority(tmp_path):
    records = [{"elev": n} for n in (10, 20, 30, 40)] + [{"elev": "n/a"}]
    column = _columns(_profile(tmp_path, records))["elev"]
    stats = column["statistics"]

    assert column["primitive_type"] == "sc:Integer"
    assert stats["jsonTypes"] == {"integer": 4, "string": 1}
    assert stats["rowCount"] == 5
    assert stats["mean"] == 25.0
    assert sum(b["count"] for b in json.loads(stats["histogram"])) == 4


def test_types_and_top_values(tmp_path):
    records = [
        {"flag": i % 3 == 0, "kind": ["a", "b", "a"][i % 3], "x": i / 2, "uid": f"u{i}"}
        for i in range(9)
    ]
    columns = _columns(_profile(tmp_path, records))

    assert columns["flag"]["primitive_type"] == "sc:Boolean"
    assert columns["x"]["primitive_type"] == "sc:Float"
    assert columns["kind"]["statistics"]["topValues"] == [
        {"value": "a", "count": 6}, {"value": "b", "count": 3},
    ]
    # Every value unique: no facet to offer.
    assert columns["uid"]["statistics"]["topValues"] is None


def test_numeric_looking_strings_stay_text(tmp_path):
    column = _columns(_profile(tmp_path, [{"code": "001"}, {"code": "002"}, {"code": "003"}]))["code"]

    assert column["primitive_type"] == "sc:Text"


def test_iso_dates_and_timestamps(tmp_path):
    records = [{"day": f"2026-09-{d:02d}", "ts": f"2026-09-{d:02d}T12:00:00Z"} for d in range(1, 6)]
    columns = _columns(_profile(tmp_path, records))

    assert columns["day"]["primitive_type"] == "sc:Date"
    assert columns["ts"]["primitive_type"] == "sc:DateTime"


def test_schema_consistency_and_depth(tmp_path):
    records = [{"a": 1, "b": {"c": [1]}}] * 3 + [{"a": 1}]
    rs = _profile(tmp_path, records)

    assert rs.schema_consistency_percentage == 75.0
    assert rs.max_depth == 3     # record, b, the list in b


# -- guardrails ----------------------------------------------------------------------

def test_objects_keyed_by_dates_collapse_to_one_wildcard_field(tmp_path):
    records = [
        {"id": i, "daily_max": {f"2026-09-{d:02d}": 20.0 + d for d in range(i, i + 12)}}
        for i in range(1, 6)
    ]
    columns = _columns(_profile(tmp_path, records))

    assert set(columns) == {"id", "daily_max.*"}
    assert columns["daily_max.*"]["repeated"] is True
    assert columns["daily_max.*"]["json_path"] == "$[*].daily_max.*"
    assert columns["daily_max.*"]["statistics"]["rowCount"] == 60


def test_path_cap_marks_the_profile_truncated(tmp_path, monkeypatch):
    monkeypatch.setattr(json_record_set, "MAX_PATHS", 3)
    rs = _profile(tmp_path, [{f"field_{i}": i for i in range(6)}])

    assert len(rs.fields) == 3
    assert rs.to_dict_cdd()["json_profile"]["paths_truncated"] is True


def test_keys_that_are_not_identifiers_use_bracket_notation(tmp_path):
    columns = _columns(_profile(tmp_path, [{"a.b": 1, "it's": 2}]))

    assert columns["a.b"]["json_path"] == "$[*]['a.b']"
    assert columns["it's"]["json_path"] == "$[*]['it\\'s']"


def test_utf8_bom_and_cp1252_files_are_read(tmp_path):
    bom = _profile(tmp_path, b"\xef\xbb\xbf" + json.dumps([{"a": 1}]).encode(),
                   name="bom.json", raw=True)
    cp1252 = _profile(tmp_path, '[{"name": "caf\xe9 – bar"}]'.encode("cp1252"),
                      name="win.json", raw=True)

    assert bom.record_count == 1
    assert _columns(cp1252)["name"]["statistics"]["topValues"] is None
    assert cp1252.fields[0].sample == ["café – bar"]


def test_long_text_is_reported_whole_for_search_and_not_faceted(tmp_path):
    note = "Rooftop station in the historic centre, next to the observatory dome. " * 3
    records = [{"id": "NOA-1", "notes": note}, {"id": "NOA-2", "notes": note}, {"id": "NOA-3"}]
    rs = _profile(tmp_path, records)
    cdd = rs.to_dict_cdd()

    assert [(c["section"], c["subsection"], c["text"]) for c in cdd["text_content"]] == [
        ("notes", "NOA-1", note), ("notes", "NOA-2", note),
    ]
    assert _columns(rs)["notes"]["statistics"]["topValues"] is None


# -- outputs ---------------------------------------------------------------------------

def test_heavy_profile_uses_croissant_json_path_and_string_statistics(tmp_path):
    rs = _profile(tmp_path, {"stations": [{"loc": {"lat": 37.9}}, {"loc": {"lat": 38.1}}]})
    record_set = rs.to_dict()
    field = record_set["field"][0]

    assert record_set["recordPath"] == "$.stations[*]"
    assert record_set["jsonShape"] == WRAPPED_RECORDS
    assert record_set["recordCount"] == 2
    assert record_set["schemaConsistencyPercentage"] == 100.0
    assert field["source"] == {
        "fileObject": {"@id": "file-1"},
        "extract": {"jsonPath": "$.stations[*].loc.lat"},
    }
    assert field["repeated"] is False
    # MoMa stores node properties flat, so JSON values are serialised, like histogram.
    assert field["statistics"]["jsonTypes"] == '{"number": 2}'
    assert "presencePercentage" not in field


def test_every_emitted_json_term_is_in_the_context(tmp_path):
    record_set = _profile(tmp_path, [{"a": "x"}, {"a": "y"}]).to_dict()
    json_terms = {"recordPath", "jsonShape", "recordCount", "maxDepth",
                  "schemaConsistencyPercentage", "jsonTypes", "topValues"}

    emitted = set(record_set) | set(record_set["field"][0]["statistics"])
    assert json_terms <= emitted
    for term in json_terms:
        assert REFERENCES_TEMPLATE[term] == f"dg:{term}"


# -- in a dataset ------------------------------------------------------------------------

@pytest.fixture
def json_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr("dataset_profiler.profile_models.DATASET_ROOT_PATH", "")
    root = tmp_path / "ds"
    (root / "articles").mkdir(parents=True)
    (root / "stations.json").write_text(json.dumps(
        {"meta": {"source": "NOA"}, "stations": [{"id": "S1", "t": 1.5}, {"id": "S2", "t": 2.5}]}
    ))
    (root / "events.ndjson").write_text('{"e": "start"}\n{"e": "stop"}\n')
    for i in range(4):
        (root / "articles" / f"a-{i}.json").write_text(json.dumps({"title": f"Article {i}"}))
    return {
        "id": "json-ds", "citeAs": "", "country": "GR",
        "data_connectors": [{"type": "RawDataPath", "dataset_id": f"{root}/"}],
        "datePublished": "2026-10-30", "description": "d", "fieldOfScience": [],
        "headline": "h", "inLanguage": ["en"], "keywords": [], "license": "CC0 1.0",
        "name": "n", "url": "", "access": "PUBLIC", "uploadedBy": "ADMIN",
    }


def test_dataset_profiles_carry_json_files(json_dataset):
    profile = DatasetProfile(json_dataset)
    heavy = profile.to_dict()
    cdd = {f["name"]: f for f in profile.to_dict_cdd()["files"]}

    assert cdd["stations"]["json_profile"]["record_path"] == "$.stations[*]"
    assert cdd["events"]["original_format"] == "jsonl"
    assert {c["name"] for c in cdd["stations"]["columns"]} == {"id", "t"}
    assert len([f for f in cdd if f.startswith("a-")]) == 4
    assert {rs["name"] for rs in heavy["recordSet"]} >= {"stations", "events", "a-0"}
    encodings = {d["name"]: d["encodingFormat"] for d in heavy["distribution"]}
    assert encodings["events.ndjson"] == "application/jsonl"


def test_heavy_profile_flag_drops_json_record_sets_but_not_cdd(json_dataset, monkeypatch):
    monkeypatch.setenv("ENABLE_JSON_RECORD_SETS", "false")
    profile = DatasetProfile(json_dataset)

    assert profile.to_dict()["recordSet"] == []
    assert any("json_profile" in f for f in profile.to_dict_cdd()["files"])


def test_llm_enrichments_are_capped_per_folder(json_dataset, monkeypatch):
    monkeypatch.setenv("JSON_LLM_MAX_FILES_PER_FOLDER", "2")
    described = []
    monkeypatch.setattr(JSONRecordSet, "_describe", lambda self: described.append(self.name))

    DatasetProfile(json_dataset).to_dict_cdd()

    articles = [name for name in described if name.startswith("a-")]
    assert len(articles) == 2                          # capped inside the folder
    assert {"stations", "events"} <= set(described)    # root files are not capped
