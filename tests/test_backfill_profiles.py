"""The backfill's graph handling, with MoMa and the profiler replaced by fakes."""

import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backfill_profiles.py"
_spec = importlib.util.spec_from_file_location("backfill_profiles", _SCRIPT)
bf = importlib.util.module_from_spec(_spec)
import sys  # noqa: E402

sys.modules["backfill_profiles"] = bf
_spec.loader.exec_module(bf)


DATASET, RS, COL, STAT, FILE = "ds", "rs-1", "col-1", "stat-1", "file-1"
CSV_LABELS = ["CSV", "Data", "cr:FileObject"]
COLUMN_LABELS = ["Column", "cr:Field"]
STATS_LABELS = ["Statistics", "dg:ColumnStatistics"]


def node(node_id, labels, **properties):
    return {"id": node_id, "labels": labels, "properties": properties}


def edge(source, target, label):
    return {"from": source, "to": target, "labels": [label], "properties": {}}


def csv_payload(path, size, column_properties=None, statistics_properties=None):
    return {
        "nodes": [
            node(DATASET, ["sc:Dataset"], type="sc:Dataset"),
            node(RS, ["cr:RecordSet"], name="table"),
            node(COL, COLUMN_LABELS, **{"name": "age", "column": "age", **(column_properties or {})}),
            node(STAT, STATS_LABELS, **{"type": "dg:ColumnStatistics", **(statistics_properties or {})}),
            node(FILE, CSV_LABELS, contentUrl=str(path), contentSize=f"{size} B"),
        ],
        "edges": [
            edge(DATASET, RS, "recordSet"),
            edge(RS, COL, "field"),
            edge(COL, STAT, "statistics"),
            edge(COL, FILE, "source/fileObject"),
        ],
    }


def document_payload(path, size, name="report", **record_set_properties):
    return {
        "nodes": [
            node(DATASET, ["sc:Dataset"], type="sc:Dataset"),
            node(RS, ["cr:RecordSet"], name=name, **record_set_properties),
            node("set-1", ["PDFSet", "Data", "cr:FileSet"]),
            node(FILE, ["PDF", "Data", "cr:FileObject"], name="report.pdf", contentUrl=str(path), contentSize=f"{size} B"),
        ],
        "edges": [edge(DATASET, RS, "recordSet"), edge(FILE, "set-1", "containedIn")],
    }


class FakeMoma:
    """Accepts deltas and applies them the way MERGE would, so read-back is real."""

    def __init__(self, payload, valid=True, lose_writes=False):
        self.payload = json.loads(json.dumps(payload))
        self.valid = valid
        self.lose_writes = lose_writes
        self.written = []
        self.validated = []

    def dataset(self, dataset_id):
        return json.loads(json.dumps(self.payload))

    def convert(self, croissant):
        record_set = croissant["recordSet"][0]
        block = record_set["dataQuality"]
        errors = block["errors"]
        return {
            "nodes": [
                node(DATASET, ["sc:Dataset"], type="sc:Dataset"),
                node(record_set["@id"], ["cr:RecordSet"]),
                node(block["@id"], ["DataQuality", "dg:DataQuality"], summary=block["summary"], type="dg:DataQuality"),
                *[
                    node(e["@id"], ["DataQualityError", "dg:DataQualityError"], column=e["column"], examples=e["examples"])
                    for e in errors
                ],
            ],
            "edges": [
                edge(DATASET, record_set["@id"], "recordSet"),
                edge(record_set["@id"], block["@id"], "HAS_DATA_QUALITY"),
                *[edge(block["@id"], e["@id"], "HAS_ERROR") for e in errors],
            ],
        }

    def validate(self, delta):
        self.validated.append(delta)
        return {"valid": self.valid}

    def write(self, delta):
        self.written.append(delta)
        if self.lose_writes:
            return
        by_id = {n["id"]: n for n in self.payload["nodes"]}
        for new in delta["nodes"]:
            if new["id"] in by_id:
                by_id[new["id"]]["properties"].update(new["properties"])
            else:
                self.payload["nodes"].append(new)
        self.payload["edges"].extend(delta["edges"])


class FakeEngine:
    max_data_quality_file_mb = 100
    min_document_words = 10

    def __init__(self, quality=None, statistics=None, annotations=None, description=None, text="word " * 40):
        self.quality = quality
        self.statistics = statistics if statistics is not None else {"age": {"@id": "x", "@type": "t", "mean": 3.5, "median": None}}
        self.annotations = annotations if annotations is not None else {"age": "patient age"}
        self.description = description or SimpleNamespace(keywords=["a", "b"], summary="sum")
        self.text = text
        self.quality_calls = 0

    def open_csv(self, path):
        return SimpleNamespace(backfill_path=path, backfill_delimiter=",", encoding="utf-8")

    def data_quality(self, handle, name):
        self.quality_calls += 1
        if isinstance(self.quality, Exception):
            raise self.quality
        return self.quality

    def csv_statistics(self, handle):
        return self.statistics

    def csv_semantic_types(self, handle, names):
        return self.annotations

    def document_text(self, path, is_pdf):
        return self.text

    def describe(self, text, name):
        return self.description


def quality_result(errors=()):
    return SimpleNamespace(to_dict=lambda: {
        "@type": "dg:DataQuality", "@id": "new-dq", "summary": "found things" if errors else "model text",
        "errors": list(errors),
    })


def backfiller(tmp_path, moma, engine, write=True, backfills="ABCD"):
    ledger = bf.Ledger(tmp_path / "ledger.jsonl", "run1", "dev", applied=write)
    options = bf.Options(backfills=set(backfills), write=write)
    return bf.Backfiller(moma, engine, ledger, options, "run1", "v0.0.35"), ledger


def lines(ledger):
    ledger.close()
    return [json.loads(line) for line in ledger.path.read_text().splitlines()]


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("age\n1\n2\n")
    return path


def test_existing_nodes_keep_their_stored_labels_and_only_gain_new_properties(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(), backfills="BC")
    runner.process(DATASET)

    sent = {n["id"]: n for n in moma.written[0]["nodes"]}
    assert sent[COL]["labels"] == COLUMN_LABELS
    assert sent[STAT]["labels"] == STATS_LABELS
    assert sent[RS]["properties"] == {}
    assert sent[COL]["properties"] == {"semanticType": "patient age"}
    assert sent[STAT]["properties"] == {"mean": 3.5}
    assert {(e["from"], e["to"]) for e in moma.written[0]["edges"]} == {(DATASET, RS), (RS, COL), (COL, STAT)}
    assert {line["outcome"] for line in lines(ledger)} == {"written"}


def test_one_write_per_dataset(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(quality=quality_result()))
    runner.process(DATASET)
    assert len(moma.written) == 1
    assert {line["backfill"] for line in lines(ledger)} == {"A", "B", "C"}


def test_dry_run_validates_but_never_writes(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(), write=False, backfills="BC")
    runner.process(DATASET)
    assert moma.written == []
    assert len(moma.validated) == 1
    assert all(line["applied"] is False for line in lines(ledger))


def test_failed_write_answered_200_is_caught_by_read_back(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size), lose_writes=True)
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(), backfills="BC")
    runner.process(DATASET)
    entries = lines(ledger)
    assert {e["outcome"] for e in entries} == {"failed"}
    assert all("read_back" in e["detail"] for e in entries)
    assert not any(e["applied"] for e in entries)


def test_invalid_delta_is_not_written(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size), valid=False)
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(), backfills="BC")
    runner.process(DATASET)
    assert moma.written == []
    assert {e["outcome"] for e in lines(ledger)} == {"failed"}


def test_changed_file_is_skipped_for_every_target(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size + 1))
    engine = FakeEngine(quality=quality_result())
    runner, ledger = backfiller(tmp_path, moma, engine)
    runner.process(DATASET)
    assert moma.validated == []
    assert engine.quality_calls == 0
    assert {e["outcome"] for e in lines(ledger)} == {"skipped_changed"}


def test_missing_file_is_recorded(tmp_path):
    moma = FakeMoma(csv_payload(tmp_path / "gone.csv", 3))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine())
    runner.process(DATASET)
    assert {e["outcome"] for e in lines(ledger)} == {"skipped_missing"}


def test_clean_table_gets_a_data_quality_node_with_the_fixed_summary(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(quality=quality_result()), backfills="A")
    runner.process(DATASET)
    new = next(n for n in moma.written[0]["nodes"] if n["id"] == "new-dq")
    assert new["properties"]["summary"] == bf.NO_ERRORS_SUMMARY
    assert new["properties"]["backfillRunId"] == "run1"
    assert new["properties"]["profilerVersion"] == "v0.0.35"
    assert "backfilledAt" in new["properties"]
    entry = lines(ledger)[0]
    assert entry["outcome"] == "clean"
    assert entry["new_node_ids"] == ["new-dq"]


def test_errors_become_nodes_and_the_existing_record_set_keeps_its_labels(tmp_path, csv_file):
    error = {"@type": "dg:DataQualityError", "@id": "new-err", "column": "age", "examples": [{"value": "-5", "row": 4}]}
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(quality=quality_result([error])), backfills="A")
    runner.process(DATASET)
    sent = {n["id"]: n for n in moma.written[0]["nodes"]}
    assert sent["new-err"]["labels"] == ["DataQualityError", "dg:DataQualityError"]
    assert "backfillRunId" not in sent["new-err"]["properties"]
    assert sent[RS]["properties"] == {}
    entry = lines(ledger)[0]
    assert entry["outcome"] == "written"
    assert set(entry["new_node_ids"]) == {"new-dq", "new-err"}


def test_existing_data_quality_is_not_redone(tmp_path, csv_file):
    payload = csv_payload(csv_file, csv_file.stat().st_size, {"semanticType": "x"}, {"mean": 1.0})
    payload["nodes"].append(node("dq-old", ["DataQuality", "dg:DataQuality"], summary="old"))
    payload["edges"].append(edge(RS, "dq-old", "HAS_DATA_QUALITY"))
    moma = FakeMoma(payload)
    engine = FakeEngine(quality=quality_result())
    runner, ledger = backfiller(tmp_path, moma, engine)
    runner.process(DATASET)
    assert engine.quality_calls == 0
    assert moma.validated == []
    assert lines(ledger) == []


@pytest.mark.parametrize(
    "result, outcome",
    [
        (None, "skipped_empty"),
        (RuntimeError("script crashed"), "failed"),
    ],
)
def test_data_quality_without_a_result_writes_nothing(tmp_path, csv_file, result, outcome):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(quality=result), backfills="A")
    runner.process(DATASET)
    assert moma.written == []
    assert lines(ledger)[0]["outcome"] == outcome


def test_too_large_file_is_not_sent_to_detection(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    engine = FakeEngine(quality=quality_result())
    engine.max_data_quality_file_mb = 0
    runner, ledger = backfiller(tmp_path, moma, engine, backfills="A")
    runner.process(DATASET)
    assert engine.quality_calls == 0
    assert lines(ledger)[0]["outcome"] == "skipped_large"


@pytest.mark.parametrize(
    "annotation, outcome",
    [("error", "failed"), (None, "skipped_empty"), ("", "skipped_empty")],
)
def test_unusable_semantic_types_are_never_written(tmp_path, csv_file, annotation, outcome):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(annotations={"age": annotation}), backfills="C")
    runner.process(DATASET)
    assert moma.written == []
    assert lines(ledger)[0]["outcome"] == outcome


def test_nan_statistics_are_dropped():
    cleaned = bf.statistics_properties(
        {"@id": "i", "@type": "t", "mean": 1.0, "variance": math.nan, "max": math.inf, "median": None, "rowCount": 0}
    )
    assert cleaned == {"mean": 1.0, "rowCount": 0}


def test_delta_with_nan_is_refused_before_reaching_moma(tmp_path, csv_file):
    graph = bf.Graph(csv_payload(csv_file, 1))
    delta = bf.Delta(graph, {})
    delta.set_properties(STAT, {"mean": math.nan})
    with pytest.raises(ValueError):
        bf.check_delta(delta)


def test_delta_with_changed_labels_is_refused(tmp_path, csv_file):
    graph = bf.Graph(csv_payload(csv_file, 1))
    delta = bf.Delta(graph, {})
    delta.set_properties(COL, {"semanticType": "x"})
    delta.nodes[COL]["labels"] = ["Column"]
    with pytest.raises(bf.MomaError):
        bf.check_delta(delta)


def test_statistics_with_values_are_left_alone(tmp_path, csv_file):
    moma = FakeMoma(csv_payload(csv_file, csv_file.stat().st_size, {"semanticType": "x"}, {"mean": 2.0}))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine())
    moma_written_before = list(moma.written)
    runner.process(DATASET)
    assert moma.written == moma_written_before


def test_document_gains_keywords_and_only_a_missing_summary(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF")
    moma = FakeMoma(document_payload(path, 4, summary=""))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine())
    runner.process(DATASET)
    sent = {n["id"]: n for n in moma.written[0]["nodes"]}
    assert sent[RS]["properties"] == {"keywords": ["a", "b"], "summary": "sum"}
    assert lines(ledger)[0]["previous"] == {"keywords": None, "summary": ""}


def test_existing_summary_is_kept(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF")
    moma = FakeMoma(document_payload(path, 4, summary="keep me"))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine())
    runner.process(DATASET)
    assert {n["id"]: n for n in moma.written[0]["nodes"]}[RS]["properties"] == {"keywords": ["a", "b"]}


def test_failed_description_is_not_written(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF")
    moma = FakeMoma(document_payload(path, 4))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(description=SimpleNamespace(keywords=[], summary="")))
    runner.process(DATASET)
    assert moma.written == []
    assert lines(ledger)[0]["outcome"] == "failed"


def test_document_with_too_little_text_is_skipped(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF")
    moma = FakeMoma(document_payload(path, 4))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine(text="too short"))
    runner.process(DATASET)
    assert lines(ledger)[0]["outcome"] == "skipped_empty"


@pytest.mark.parametrize("name", ["report", "report.pdf", "/s3/dataset/abc/report.pdf", "/s3/dataset/abc/report"])
def test_document_names_in_every_stored_form_match(tmp_path, name):
    graph = bf.Graph(document_payload("/s3/dataset/abc/report.pdf", 4, name=name))
    matched, _ = bf.match_document_file(graph, graph.nodes[RS])
    assert matched["id"] == FILE


def test_ambiguous_document_name_is_not_guessed():
    payload = document_payload("/s3/dataset/abc/report.pdf", 4)
    payload["nodes"].append(node("file-2", ["Text", "Data", "cr:FileObject"], name="report.txt", contentUrl="/s3/x/report.txt"))
    graph = bf.Graph(payload)
    matched, reason = bf.match_document_file(graph, graph.nodes[RS])
    assert matched is None
    assert reason == "ambiguous_name"


@pytest.mark.parametrize(
    "url, expected",
    [("s3://dataset/a/b.csv", "/s3/dataset/a/b.csv"), ("/s3/dataset/a/b.csv", "/s3/dataset/a/b.csv")],
)
def test_content_urls_resolve_to_the_mount(url, expected):
    assert bf.normalize_content_url(url) == expected


@pytest.mark.parametrize("value, expected", [("2010494 B", 2010494), ("12B", 12), ("2 MB", None), (None, None)])
def test_content_size_parsing(value, expected):
    assert bf.parse_content_size(value) == expected


def test_unreadable_dataset_is_recorded_and_stops_only_when_asked(tmp_path, csv_file):
    class Broken(FakeMoma):
        def dataset(self, dataset_id):
            raise bf.DatasetUnreadable("HTTP 500")

    moma = Broken(csv_payload(csv_file, 1))
    runner, ledger = backfiller(tmp_path, moma, FakeEngine())
    runner.process(DATASET)
    assert lines(ledger)[0]["outcome"] == "unreadable"

    ledger2 = bf.Ledger(tmp_path / "other.jsonl", "r", "prod", applied=False)
    stopping = bf.Backfiller(moma, FakeEngine(), ledger2, bf.Options(stop_on_unreadable=True), "r", "v")
    with pytest.raises(bf.StopRun):
        stopping.process(DATASET)


class FakeDatabase:
    """Answers the statistics queries, and records the SQL it was given."""

    def __init__(self, aggregates, buckets=()):
        self.aggregates = aggregates
        self.buckets = buckets
        self.queries = []

    def __call__(self, sql):
        self.queries.append(sql)
        if "width_bucket" in sql:
            return pd.DataFrame(self.buckets, columns=["bucket", "rows_in_bucket"])
        return pd.DataFrame([self.aggregates])


NUMERIC_ROW = {
    "total": 10, "present": 8, "mean_value": 5.0, "std_value": 1.0, "variance_value": 1.0,
    "low": 0.0, "high": 10.0, "p05": 0.5, "p50": 5.0, "p95": 9.5,
}


def test_db_numeric_statistics_count_missing_values_and_keep_the_maximum():
    database = FakeDatabase(NUMERIC_ROW, buckets=[(1, 3), (10, 5)])
    stats = bf.compute_db_statistics(database, "Readings", "Temp C", "sc:Integer", ColumnStatistics)
    assert stats["rowCount"] == 8
    assert stats["missingCount"] == 2
    assert stats["missingPercentage"] == 20.0
    assert stats["range"] == 10.0
    histogram = json.loads(stats["histogram"])
    assert len(histogram) == 10
    assert histogram[0] == {"binRange": [0.0, 1.0], "count": 3}
    assert histogram[9] == {"binRange": [9.0, 10.0], "count": 5}
    assert sum(b["count"] for b in histogram) == 8
    assert all('"Readings"' in q and '"Temp C"' in q for q in database.queries)
    assert not any("LIMIT" in q for q in database.queries)


def test_db_constant_column_has_a_histogram_without_querying_for_one():
    database = FakeDatabase({**NUMERIC_ROW, "low": 4.0, "high": 4.0})
    stats = bf.compute_db_statistics(database, "t", "c", "sc:Float", ColumnStatistics)
    assert len(database.queries) == 1
    assert sum(b["count"] for b in json.loads(stats["histogram"])) == 8


def test_db_all_null_numeric_column():
    database = FakeDatabase({**NUMERIC_ROW, "present": 0, "low": None, "high": None})
    stats = bf.compute_db_statistics(database, "t", "c", "sc:Integer", ColumnStatistics)
    assert stats["rowCount"] == 0
    assert stats["missingCount"] == 10
    assert stats["missingPercentage"] == 100.0


def test_db_text_statistics():
    database = FakeDatabase({"total": 4, "present": 3, "unique_values": 2})
    stats = bf.compute_db_statistics(database, "t", "c", "sc:Text", ColumnStatistics)
    assert (stats["rowCount"], stats["missingCount"], stats["uniqueCount"]) == (3, 1, 2)
    assert stats["missingPercentage"] == 25.0


def test_db_empty_table_gives_nothing_to_write():
    database = FakeDatabase({"total": 0, "present": 0, "unique_values": 0})
    stats = bf.compute_db_statistics(database, "t", "c", "sc:Text", ColumnStatistics)
    assert bf.statistics_properties(stats) == {}


def test_db_query_error_is_raised_not_written():
    with pytest.raises(bf.MomaError, match="boom"):
        bf.compute_db_statistics(lambda sql: {"error": "boom"}, "t", "c", "sc:Text", ColumnStatistics)


@pytest.mark.parametrize(
    "name, quoted",
    [("Temp", '"Temp"'), ('a"b', '"a""b"'), ("a:b", '"a\\:b"')],
)
def test_identifier_quoting(name, quoted):
    assert bf.quote_identifier(name) == quoted


@pytest.mark.parametrize("estimate", [-1, 0, 100])
def test_table_within_the_limit_or_without_an_estimate_goes_ahead(estimate):
    bf.check_table_size(lambda sql: pd.DataFrame([{"estimate": estimate}]), "t", 100)


def test_huge_table_is_refused_from_the_estimate_alone():
    queries = []

    def execute(sql):
        queries.append(sql)
        return pd.DataFrame([{"estimate": 735_000_000}])

    with pytest.raises(bf.TableTooLarge):
        bf.check_table_size(execute, "landcover", 10_000_000)
    assert len(queries) == 1
    assert "pg_class" in queries[0]


def test_huge_table_is_recorded_as_skipped_large(tmp_path):
    class Engine(FakeEngine):
        def db_statistics(self, connection, table, column, data_type):
            raise bf.TableTooLarge("about 735000000 rows")

    runner, ledger = backfiller(tmp_path, FakeMoma(csv_payload("/x", 1)), Engine())
    graph = bf.Graph(csv_payload("/x", 1))
    table = bf.TableSource("db", graph.nodes[RS], graph.nodes[FILE], [graph.nodes[COL]])
    delta, entries = bf.Delta(graph, {}), []
    runner._table_statistics_db(DATASET, table, object(), [(graph.nodes[COL], graph.nodes[STAT])], delta, entries)
    assert entries[0]["outcome"] == "skipped_large"
    assert delta.is_empty


def test_engine_comes_from_the_connection_port_whatever_the_host(monkeypatch):
    monkeypatch.setenv("DATAGEMS_TIMESCALE_DB_PORT", "30433")
    monkeypatch.setenv("DATAGEMS_POSTGRES_PORT", "30432")
    assert bf.database_engine(node("c", [], contentUrl="postgresql://172.16.59.5:30433/db")) == "TimescaleDB"
    assert bf.database_engine(node("c", [], contentUrl="postgresql://172.16.59.5:30432/db")) == "PostgreSQL"
    with pytest.raises(bf.MomaError):
        bf.database_engine(node("c", [], contentUrl="postgresql://172.16.59.5:5432/db"))


def test_older_documents_labelled_with_their_set_are_matched():
    payload = document_payload("/s3/dataset/abc/report.pdf", 4, name="report.pdf")
    next(n for n in payload["nodes"] if n["id"] == FILE)["labels"] = ["Data", "cr:FileObject", "PDFSet"]
    graph = bf.Graph(payload)
    matched, _ = bf.match_document_file(graph, graph.nodes[RS])
    assert matched["id"] == FILE


def test_pdf_text_comes_from_whichever_function_the_image_has():
    older = SimpleNamespace(parse_and_chunk_pdf=lambda path: ("the text", ["chunk"]))
    newer = SimpleNamespace(parse_pdf=lambda path: "the text")
    assert bf.pdf_text_reader(older)("a.pdf") == "the text"
    assert bf.pdf_text_reader(newer)("a.pdf") == "the text"
    with pytest.raises(SystemExit):
        bf.pdf_text_reader(SimpleNamespace())


def test_production_write_needs_explicit_confirmation():
    args = bf.parse_args(["run", "--env", "prod", "--dataset", "x", "--write"])
    with pytest.raises(SystemExit, match="confirm-prod"):
        bf.run(args)


def test_writing_everything_needs_explicit_confirmation():
    args = bf.parse_args(["run", "--env", "dev", "--all", "--write"])
    with pytest.raises(SystemExit, match="confirm-all"):
        bf.run(args)
