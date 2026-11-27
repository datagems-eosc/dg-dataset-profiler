"""Non-ASCII text inside JSON-string properties stays readable after one parse.

``examples``, ``jsonTypes`` and ``topValues`` are JSON strings inside the
profile (MoMa stores flat values). Written with \\u escapes, a reader saw
"\\u0393\\u03a1..." after parsing the profile and needed a second json.loads to
get "ΓΡΑΜΜΗ 3". The value is still a JSON string, with the same content.
"""

import json

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.csv.csv_record_set import CSVRecordSet
from dataset_profiler.profile_components.record_set.db.db_record_set import DBTableField


def test_csv_examples_keep_greek_text(tmp_path):
    (tmp_path / "lines.csv").write_text("γραμμή,στάσεις\nΓΡΑΜΜΗ 3,12\nΓΡΑΜΜΗ 7,9\n", encoding="utf-8")
    examples = CSVRecordSet(str(tmp_path), "lines.csv", "file-id").to_dict()["examples"]
    assert isinstance(examples, str)
    assert "ΓΡΑΜΜΗ 3" in examples and "\\u" not in examples
    assert json.loads(examples) == {"γραμμή": ["ΓΡΑΜΜΗ 3", "ΓΡΑΜΜΗ 7"], "στάσεις": [12, 9]}


def test_db_examples_keep_greek_text():
    table = DBTableField.__new__(DBTableField)
    table.type, table.id, table.name, table.fields = "cr:RecordSet", "t-id", "lines", []
    table.examples = {"line": ["ΓΡΑΜΜΗ 3"]}
    examples = table.to_dict()["examples"]
    assert "ΓΡΑΜΜΗ 3" in examples
    assert json.loads(examples) == {"line": ["ΓΡΑΜΜΗ 3"]}


def test_json_field_statistics_keep_greek_text():
    statistics = ColumnStatistics(json_types={"string": 2},
                                  top_values=[{"value": "Αθήνα", "count": 2}]).to_dict()
    assert "Αθήνα" in statistics["topValues"]
    assert json.loads(statistics["topValues"]) == [{"value": "Αθήνα", "count": 2}]
    assert json.loads(statistics["jsonTypes"]) == {"string": 2}
