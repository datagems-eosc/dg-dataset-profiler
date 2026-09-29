"""Semantic type answers are normalised so formatting differences between runs vanish."""

import pytest

from dataset_profiler.profile_components.cta import finalize_semantic_type, normalize_semantic_type


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


@pytest.mark.parametrize("label, header", [
    ("date", "Date"),
    ("patient name", "patient_name"),
    ("email", "email"),
    ("boarding disembark", "boarding_disembark_desc"),
    ("validation", "dv_validations"),
    ("date hour", "dateHour"),
    ("routes per hour", "routes_per_hour"),
    ("phone number", "phone"),                    # filler words add nothing
    ("email address", "instructor_email"),
    ("station name", "dv_platenum_station"),
])
def test_label_that_repeats_the_header_is_dropped(label, header):
    assert finalize_semantic_type(label, header) is None


@pytest.mark.parametrize("label, header", [
    ("systolic blood pressure", "systolic_bp"),   # expands an abbreviation
    ("municipality", "Kommune"),                  # translates the header
    ("temperature", "T_mean"),
    ("load date", "load_dt"),
    ("identifier", "id"),                         # reserved values are never dropped
    ("unknown", "unknown"),
    ("name", "full_title"),                       # a label of only filler is not an echo
])
def test_label_that_adds_information_is_kept(label, header):
    assert finalize_semantic_type(label, header) == label


@pytest.mark.parametrize("raw", ["none", "None.", "NULL", "  none  "])
def test_explicit_no_label_answer_becomes_none(raw):
    assert finalize_semantic_type(raw, "whatever") is None
