"""Encoding resolution for tabular files.

The profiler used to read every CSV as ISO-8859-1, which never raises but
silently mangles UTF-8 content. These tests pin the ladder that replaced it.
"""

import pytest

from dataset_profiler.utilities import resolve_encoding


def _write(tmp_path, name, payload: bytes):
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def test_plain_ascii_resolves_to_utf8(tmp_path):
    path = _write(tmp_path, "a.csv", b"col\nvalue\n")
    assert resolve_encoding(path) == "utf-8-sig"


def test_utf8_content_resolves_to_utf8(tmp_path):
    path = _write(tmp_path, "greek.csv", "station\nΑΓΙΑ ΒΑΡΒΑΡΑ\n".encode("utf-8"))
    assert resolve_encoding(path) == "utf-8-sig"


def test_utf8_bom_is_stripped_from_the_first_column(tmp_path):
    """A BOM read as Latin-1 welds 'ï»¿' onto the first column name."""
    path = _write(tmp_path, "bom.csv", b"\xef\xbb\xbfKategorie;Art\nx;y\n")
    encoding = resolve_encoding(path)
    assert encoding == "utf-8-sig"
    assert path.read_text(encoding=encoding).startswith("Kategorie")


def test_windows_punctuation_falls_back_to_cp1252(tmp_path):
    """0x96 is an en-dash in cp1252 and an unusable control char in Latin-1."""
    path = _write(tmp_path, "excel.csv", b"pages\n893 \x96 897\n")
    encoding = resolve_encoding(path)
    assert encoding == "cp1252"
    assert "–" in path.read_text(encoding=encoding)


def test_bytes_undefined_in_cp1252_fall_through_to_latin1(tmp_path):
    """0x9d has no cp1252 mapping, so the never-fails rung has to catch it."""
    path = _write(tmp_path, "odd.csv", b"col\nvalue \x9d here\n")
    assert resolve_encoding(path) == "ISO-8859-1"


def test_encoding_is_decided_by_the_whole_file_not_a_prefix(tmp_path):
    """A prefix probe would call this UTF-8 and then crash mid-stream."""
    payload = b"col\n" + (b"ascii row\n" * 200_000) + b"late \x92 byte\n"
    path = _write(tmp_path, "late.csv", payload)
    assert payload[:200_000].decode("utf-8")  # prefix alone looks like UTF-8
    assert resolve_encoding(path) != "utf-8-sig"


def test_missing_file_reports_the_safe_fallback(tmp_path):
    """Callers open the file next and raise a better error than this can."""
    assert resolve_encoding(tmp_path / "nope.csv") == "ISO-8859-1"


@pytest.mark.parametrize("payload", [b"", b"\n"])
def test_trivial_files_do_not_raise(tmp_path, payload):
    path = _write(tmp_path, "empty.csv", payload)
    assert resolve_encoding(path) == "utf-8-sig"
