"""Keywords and summaries of PDF and text record sets, with the LLM faked.

The live counterpart is ``tests/test_ipb_offering.py``.
"""

import json

import pytest

from dataset_profiler.profile_components.record_set import document_description
from dataset_profiler.profile_components.record_set.document_description import (
    MAX_INPUT_CHARS,
    MAX_KEYWORDS,
    describe_document,
    parse_description,
)
from dataset_profiler.profile_models import DatasetProfile

IPB_SPEC = "tests/assets/ipb_offering/specifications.json"

# Long enough to clear MIN_INPUT_WORDS, so the LLM is actually reached.
SOME_TEXT = "This course unit introduces machine learning with Python and Scikit-Learn."

FAKE_ANSWER = json.dumps(
    {
        "keywords": ["Artificial Intelligence", "Machine Learning", "Python"],
        "summary": "A third-year course unit on machine learning with Python.",
    }
)


@pytest.fixture
def fake_llm(monkeypatch):
    """Turn document descriptions on and record the prompts instead of calling SCAYLE."""
    monkeypatch.setenv("ENABLE_DOCUMENT_LLM", "true")
    prompts = []

    def _fake_call(prompt):
        prompts.append(prompt)
        return FAKE_ANSWER

    monkeypatch.setattr(document_description, "_call_llm", _fake_call)
    return prompts


def test_parse_description_strips_fences_and_duplicates():
    raw = '```json\n{"keywords": ["AI", "ai", " Python ", ""], "summary": " Short. "}\n```'
    description = parse_description(raw)
    assert description.keywords == ["AI", "Python"]
    assert description.summary == "Short."


def test_parse_description_caps_keywords():
    raw = json.dumps({"keywords": [f"k{i}" for i in range(20)], "summary": ""})
    assert len(parse_description(raw).keywords) == MAX_KEYWORDS


def test_describe_document_truncates_long_text(fake_llm):
    text = "word " * (MAX_INPUT_CHARS // 5) + "TAIL_MARKER"
    describe_document(text, name="long.pdf")
    assert "word word" in fake_llm[0]
    assert "TAIL_MARKER" not in fake_llm[0]


@pytest.mark.parametrize("text", ["   ", "#", "Page 1 of 2"])
def test_describe_document_skips_near_empty_text(fake_llm, text):
    description = describe_document(text, name="scanned.pdf")
    assert description.keywords == [] and description.summary == ""
    assert fake_llm == []


def test_describe_document_degrades_on_bad_answer(monkeypatch):
    monkeypatch.setenv("ENABLE_DOCUMENT_LLM", "true")
    calls = []
    monkeypatch.setattr(
        document_description, "_call_llm", lambda prompt: calls.append(prompt) or "not json"
    )
    description = describe_document(SOME_TEXT, name="doc.pdf")
    assert len(calls) == 1
    assert description.keywords == [] and description.summary == ""


def test_describe_document_disabled_makes_no_call(monkeypatch):
    monkeypatch.setenv("ENABLE_DOCUMENT_LLM", "false")

    def _fail(prompt):
        raise AssertionError("LLM called while disabled")

    monkeypatch.setattr(document_description, "_call_llm", _fail)
    assert describe_document(SOME_TEXT).keywords == []


def test_pdf_keywords_and_summary_reach_both_profiles(fake_llm):
    with open(IPB_SPEC) as f:
        spec = json.load(f)
    profile = DatasetProfile(spec)
    heavy = profile.to_dict()

    # One call for the single PDF, and the prompt carries its extracted text.
    assert len(fake_llm) == 1
    assert "Scikit-Learn" in fake_llm[0]

    (record_set,) = heavy["recordSet"]
    assert record_set["keywords"] == ["Artificial Intelligence", "Machine Learning", "Python"]
    assert record_set["summary"].startswith("A third-year course unit")

    cdd_files = [
        f for f in profile.to_dict_cdd()["files"] if f["original_format"] == "application/pdf"
    ]
    assert len(cdd_files) == 1
    assert cdd_files[0]["keywords"] == record_set["keywords"]
    assert cdd_files[0]["description"] == record_set["summary"]
