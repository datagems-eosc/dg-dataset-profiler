"""The structure of a profile, for the structure regression test (handoff 12c, Rule 1).

``build_dataset`` writes a fixed dataset -- CSV, an xlsx with an empty sheet,
JSON, PDF, text, a file set and a stubbed database -- and ``profile_structure``
profiles it offline (no LLM, no database server) and reduces both outputs to
their structure: every key path, list indices collapsed, with the JSON kinds of
the values found there. Values themselves are ignored.

The module has no dependency on the code under test beyond the profiler's
public entry points, so it also runs against older commits: that is how
``tests/data/profile_structure_baseline.json`` was made (run this file as a
script from the older checkout, see ``main``).
"""

import json
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

DATASET_ID = "8930240b-a0e8-46e7-ace8-aab2b42fcc01"


def build_dataset(root: Path) -> Path:
    """Write the fixed dataset under ``root`` and return its folder."""
    import pandas as pd

    folder = root / DATASET_ID
    folder.mkdir(parents=True)
    rows = []
    for i in range(300):
        rows.append(",".join([
            str(i),                                   # int
            "" if i % 7 == 0 else f"{i * 1.5}",       # float with missing values
            "true" if i % 3 else "false",             # boolean
            f"{i:05d}",                               # leading zeros
            f"name {i % 11}",                         # text
            f"2024-01-{i % 28 + 1:02d}",              # date
            "" if i % 5 else str(i),                  # int with many missing values
            "",                                       # all missing
            str(i) if i < 295 else "word",            # mixed
        ]))
    (folder / "table.csv").write_text(
        "id,price,active,zip,label,day,sparse,empty,mixed\n" + "\n".join(rows) + "\n"
    )

    with pd.ExcelWriter(folder / "book.xlsx") as writer:
        pd.DataFrame({"answer": ["yes", "no", "yes"], "score": [1, 2, 3]}).to_excel(
            writer, sheet_name="Responses", index=False)
        pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        pd.DataFrame({"n": [1.5, 2.5, 3.5], "flag": [True, False, True]}).to_excel(
            writer, sheet_name="Numbers", index=False)

    records = [
        {"id": i, "name": f"station {i}", "active": bool(i % 2), "opened": f"2020-01-{i % 28 + 1:02d}",
         "location": {"lat": 37.0 + i / 100, "lon": 23.0 - i / 100},
         "readings": [{"temp": 20 + j, "ok": True} for j in range(i % 3)]}
        for i in range(40)
    ]
    (folder / "stations.json").write_text(json.dumps(records))

    (folder / "notes.txt").write_text(
        "Weather stations measure temperature, humidity and wind across the country. " * 20)
    _write_pdf(folder / "report.pdf")

    subfolder = folder / "extra"
    subfolder.mkdir()
    (subfolder / "more.json").write_text(json.dumps([{"k": i, "v": f"x{i}"} for i in range(10)]))
    (subfolder / "readme.txt").write_text("A folder of extra records for the test dataset. " * 20)
    return folder


def _write_pdf(path: Path):
    import fitz  # pymupdf

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "A short report about weather stations and their readings. " * 3)
    document.set_metadata({"title": "Report", "author": "Tester", "subject": "Weather",
                           "creator": "test", "producer": "test"})
    document.save(str(path))
    document.close()


def specification(data_root: str) -> dict:
    return {
        "id": DATASET_ID,
        "citeAs": "",
        "country": "GR",
        "datePublished": "2025-01-01",
        "description": "A dataset for the structure regression test.",
        "fieldOfScience": ["EARTH SCIENCES"],
        "headline": "Structure test",
        "inLanguage": ["en"],
        "keywords": ["test"],
        "license": "CC0 1.0",
        "name": "Structure test",
        "url": "",
        "access": "NOT IMPLEMENTED",
        "uploadedBy": "ADMIN",
        "data_connectors": [
            {"type": "RawDataPath", "dataset_id": DATASET_ID + "/"},
            {"type": "DatabaseConnection", "database_name": "ds_test", "protocol": "postgresql",
             "engine": "PostgreSQL", "host": "localhost", "port": 5432},
        ],
    }


# -- the stubbed database ---------------------------------------------------------------

_SCHEMA = [{
    "table_name": "readings",
    "columns": [
        {"column": "id", "data_type": "INTEGER", "values": [1, 2, 3], "is_pk": True, "foreign_keys": []},
        {"column": "payload", "data_type": "JSONB", "values": [{"k": 702}, {"k": 1}], "is_pk": False,
         "foreign_keys": []},
        {"column": "tags", "data_type": "ARRAY", "values": [["a", "b"]], "is_pk": False, "foreign_keys": []},
        {"column": "taken", "data_type": "TIMESTAMP WITH TIME ZONE", "values": ["2024-01-01 00:00:00+00"],
         "is_pk": False, "foreign_keys": []},
    ],
}]


class _FakeDatabase:
    def __init__(self, *args, **kwargs):
        pass

    def get_tables_and_columns(self, *args, **kwargs):
        return {"tables": [t["table_name"] for t in _SCHEMA]}


def _fake_sample(*args, **kwargs):
    import pandas as pd
    return pd.DataFrame({"id": [1, 2], "payload": [{"k": 702}, {"k": 1}], "tags": [["a"], ["b"]],
                         "taken": ["2024-01-01", "2024-01-02"]})


def _offline_patches(stack: ExitStack):
    """No LLM, no database server, no data quality."""
    from dataset_profiler.profile_components import cta, distribution
    from dataset_profiler.profile_components.record_set.db import db_record_set

    stack.enter_context(mock.patch.object(cta.ColumnTypeAnnotator, "__init__", lambda self, *a, **k: None))
    stack.enter_context(mock.patch.object(cta.ColumnTypeAnnotator, "annotate_columns", lambda self, *a, **k: {}))
    stack.enter_context(mock.patch.object(distribution, "DatagemsPostgres", _FakeDatabase))
    stack.enter_context(mock.patch.object(db_record_set, "DatagemsPostgres", _FakeDatabase))
    stack.enter_context(mock.patch.object(db_record_set, "obtain_schema_from_db", lambda *a, **k: _SCHEMA))
    stack.enter_context(mock.patch.object(db_record_set, "get_table_sample", _fake_sample))
    stack.enter_context(mock.patch.dict(os.environ, {
        "ENABLE_DATA_QUALITY": "false",
        "ENABLE_DOCUMENT_LLM": "false",
        "ENABLE_DB_STATISTICS": "false",
        "ENABLE_JSON_RECORD_SETS": "true",
        "DATAGEMS_POSTGRES_HOST": "localhost",
        "DATAGEMS_POSTGRES_PORT": "5432",
    }))


def profile_dataset(root: Path) -> dict:
    """The heavy MoMa profile and the CDD profile of the fixed dataset under ``root``."""
    build_dataset(root)
    with ExitStack() as stack:
        _offline_patches(stack)
        from dataset_profiler import profile_models
        stack.enter_context(mock.patch.object(profile_models, "DATASET_ROOT_PATH", str(root) + "/"))
        profile = profile_models.DatasetProfile(specification(str(root)))
        profile.distributions = profile.extract_distributions()
        profile.record_sets = profile.extract_record_sets()
        return {"moma": profile.to_dict(), "cdd": profile.to_dict_cdd()}


# -- structure ----------------------------------------------------------------------

def _kind(value) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "null"   # NaN serialises as NaN/null; it is a missing number either way
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    return "array"


# Lists whose items are told apart by a key, so a path names one record set or
# field rather than the union of all of them. Every other list collapses to [].
_ITEM_KEYS = {"recordSet": "name", "field": "name", "distribution": "@type", "files": "name",
              "columns": "name", "tables": "name"}


def structure(value, path: str = "$", out=None) -> dict:
    """``{path: sorted kinds}`` for every key path of ``value``."""
    if out is None:
        out = {}
    out.setdefault(path, set()).add(_kind(value))
    if isinstance(value, dict):
        for key, child in value.items():
            structure(child, f"{path}.{key}", out)
    elif isinstance(value, list):
        list_name = path.rsplit(".", 1)[-1].split("[", 1)[0]
        item_key = _ITEM_KEYS.get(list_name)
        for item in value:
            if item_key and isinstance(item, dict) and item_key in item:
                structure(item, f"{path}[{item_key}={item[item_key]}]", out)
            else:
                structure(item, f"{path}[]", out)
    return out


def profile_structure(root: Path) -> dict:
    profiles = profile_dataset(root)
    # Some names hold the absolute path of the file (text record sets): drop
    # the temporary root so the structure is the same wherever it runs.
    prefix = str(root)
    return {
        name: {path.replace(prefix, "<root>"): sorted(kinds) for path, kinds in sorted(structure(profile).items())}
        for name, profile in profiles.items()
    }


def main():
    """Write the structure of the profile to the path given (from any checkout)."""
    import tempfile

    out = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as tmp:
        result = profile_structure(Path(tmp))
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
