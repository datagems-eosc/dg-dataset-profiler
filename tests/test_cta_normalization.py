"""Semantic type answers are normalised so formatting differences between runs vanish."""

import pytest

from dataset_profiler.profile_components.cta import normalize_semantic_type


@pytest.mark.parametrize("raw", [
    "attendance_percentage",
    "Attendance percentage.",
    '"attendance percentage"',
    "  **Attendance Percentage**  ",
    "attendance   percentage",
])
def test_formatting_variants_collapse_to_one_form(raw):
    assert normalize_semantic_type(raw) == "attendance percentage"


def test_echoed_header_and_extra_lines_are_dropped():
    """Seen when a whole semicolon row was sent as one column."""
    assert normalize_semantic_type("reading_id: identifier\nstation_code: code") == "identifier"


@pytest.mark.parametrize("raw, expected", [
    ("pm2.5", "pm2.5"),            # internal punctuation is meaning, not formatting
    ("e-mail address", "e-mail address"),
    ("", "unknown"),
    ("   ", "unknown"),
    ("unknown", "unknown"),
])
def test_meaningful_content_is_preserved(raw, expected):
    assert normalize_semantic_type(raw) == expected
