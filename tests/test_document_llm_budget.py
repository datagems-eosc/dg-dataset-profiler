"""The per-job time budget on document keywords and summaries."""

import json

import pytest

from dataset_profiler.profile_components.record_set import document_description
from dataset_profiler.profile_components.record_set.document_description import (
    DocumentDescription,
    describe_document,
    document_llm_time_budget,
)

TEXT = "This course unit introduces integration by parts and trigonometric substitution."
ANSWER = json.dumps({"keywords": ["integration by parts"], "summary": "Integration techniques."})


@pytest.fixture
def slow_llm(monkeypatch):
    """Each call takes 4 fake seconds; records the timeout it was given."""
    monkeypatch.setenv("ENABLE_DOCUMENT_LLM", "true")
    monkeypatch.setenv("DOCUMENT_LLM_TIMEOUT", "120")
    clock = {"now": 0.0}
    timeouts = []

    def fake_call(prompt, timeout):
        timeouts.append(timeout)
        clock["now"] += 4.0
        return ANSWER

    monkeypatch.setattr(document_description, "_call_llm", fake_call)
    monkeypatch.setattr(document_description.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(document_description, "MIN_CALL_SECONDS", 1.0)
    return timeouts


def test_documents_past_the_budget_get_no_description(slow_llm):
    with document_llm_time_budget(10) as budget:
        results = [describe_document(TEXT, name=f"doc{i}") for i in range(5)]

    # 4s + 4s + 4s: the third call starts with 2s left and overruns; the rest are skipped.
    assert [bool(r.keywords) for r in results] == [True, True, True, False, False]
    assert budget.skipped_documents == 2
    # Each call may only take what is left of the budget.
    assert slow_llm == [10.0, 6.0, 2.0]


def test_call_timeout_is_capped_by_what_is_left(slow_llm, monkeypatch):
    monkeypatch.setenv("DOCUMENT_LLM_TIMEOUT", "30")
    with document_llm_time_budget(6):
        describe_document(TEXT)
        describe_document(TEXT)
    assert slow_llm == [6.0, 2.0]


def test_failed_calls_count_against_the_budget(monkeypatch):
    monkeypatch.setenv("ENABLE_DOCUMENT_LLM", "true")
    clock = {"now": 0.0}

    def failing_call(prompt, timeout):
        clock["now"] += 50.0
        raise TimeoutError("SCAYLE did not answer")

    monkeypatch.setattr(document_description, "_call_llm", failing_call)
    monkeypatch.setattr(document_description.time, "monotonic", lambda: clock["now"])
    with document_llm_time_budget(60) as budget:
        assert describe_document(TEXT) == DocumentDescription()
        assert budget.remaining() == 10.0


def test_zero_budget_means_no_limit(slow_llm):
    with document_llm_time_budget(0) as budget:
        results = [describe_document(TEXT) for _ in range(5)]
    assert budget is None
    assert all(r.keywords for r in results)


def test_budget_defaults_to_the_environment(monkeypatch):
    monkeypatch.setenv("DOCUMENT_LLM_TIME_BUDGET_SECONDS", "42")
    with document_llm_time_budget() as budget:
        assert budget.seconds == 42.0


def test_no_budget_outside_a_profiling_job(slow_llm):
    results = [describe_document(TEXT) for _ in range(3)]
    assert all(r.keywords for r in results)
