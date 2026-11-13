"""CDD matches files on the exact "original_format" strings.

Reported by CDD: a PDF sometimes came through as "pdf" rather than
"application/pdf" and was indexed as an unknown type. A file whose record set
is not extracted (a root-level document, an unreadable one, an upper-case
extension) was given its bare extension, while profiled files got the
canonical value. Both paths now share one mapping.
"""

from pathlib import Path

import pytest

from dataset_profiler.profile_components.distribution import get_original_format
from dataset_profiler.profile_models import DatasetProfile


@pytest.mark.parametrize("path, expected", [
    ("a/b.pdf", "application/pdf"),
    ("a/b.PDF", "application/pdf"),
    ("b.txt", "text"),
    ("b.csv", "csv"),
    ("b.xlsx", "xlsx"),
    ("b.xls", "xlsx"),
    ("b.json", "json"),
    ("b.geojson", "json"),
    ("b.jsonl", "jsonl"),
    ("b.ndjson", "jsonl"),
    ("b.DOCX", "docx"),
    ("b.m4a", "m4a"),
])
def test_original_format_from_extension(path, expected):
    assert get_original_format(path) == expected


def test_files_without_record_set_get_the_canonical_format(tmp_path, monkeypatch):
    monkeypatch.setattr("dataset_profiler.profile_models.DATASET_ROOT_PATH", "")
    root = tmp_path / "ds"
    root.mkdir()
    (root / "report.pdf").write_bytes(b"not really a pdf")
    (root / "notes.txt").write_text("Some notes.")
    (root / "recording.m4a").write_bytes(b"\x00" * 10)

    profile = DatasetProfile({
        "id": "test-id",
        "citeAs": "",
        "country": "PT",
        "data_connectors": [{"type": "RawDataPath", "dataset_id": f"{root}/"}],
        "datePublished": "2025-08-23",
        "description": "d",
        "fieldOfScience": [],
        "headline": "h",
        "inLanguage": ["en"],
        "keywords": [],
        "license": "CC0 1.0",
        "name": "n",
        "url": "",
        "access": "PUBLIC",
        "uploadedBy": "ADMIN",
    }).to_dict_cdd()

    formats = {Path(f["source_file"]).name: f["original_format"] for f in profile["files"]}
    assert formats == {
        "report.pdf": "application/pdf",
        "notes.txt": "text",
        "recording.m4a": "m4a",
    }
