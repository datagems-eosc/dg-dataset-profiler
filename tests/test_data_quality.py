import json
from pathlib import Path

import pandas as pd
import pytest
import requests
from litellm.exceptions import AuthenticationError
from pydantic import ValidationError

from dataset_profiler.common_llm.scayle_auth import ScayleAuthClient
from dataset_profiler.data_quality import llm as dq_llm
from dataset_profiler.data_quality.data_profile import build_profile
from dataset_profiler.data_quality.detector import is_data_quality_enabled
from dataset_profiler.data_quality.executor import (
    _extract_code,
    execute_detection_script,
)
from dataset_profiler.data_quality.models import (
    ColumnError,
    DataQualityResult,
    ErrorExample,
)
from dataset_profiler.data_quality.prompts import _format_error_for_summary

SAMPLE_CSV = Path(__file__).parent / "assets" / "data_quality" / "patients.csv"


# --- Models ---


def test_error_example_basic():
    ex = ErrorExample(value="999%", row=5)
    assert ex.value == "999%"
    assert ex.row == 5


def test_column_error_basic():
    err = ColumnError(
        column="humidity_pct",
        error_type="value_error",
        description="Values exceed 100%",
        examples=[ErrorExample(value="999%", row=5)],
        total_affected_rows=3,
    )
    assert err.column == "humidity_pct"
    assert len(err.examples) == 1


def test_column_error_requires_fields():
    with pytest.raises(ValidationError):
        ColumnError(column="a")


def test_data_quality_result_total_affected_rows():
    result = DataQualityResult(
        summary="Two issues found.",
        errors=[
            ColumnError(
                column="col1",
                error_type="value_error",
                description="desc",
                examples=[],
                total_affected_rows=10,
            ),
            ColumnError(
                column="col2",
                error_type="format_inconsistency",
                description="desc",
                examples=[],
                total_affected_rows=5,
            ),
        ],
    )
    assert result.total_affected_rows == 15


def test_data_quality_result_to_dict_camel_case():
    result = DataQualityResult(
        summary="One issue.",
        errors=[
            ColumnError(
                column="age",
                error_type="value_error",
                description="Negative ages",
                examples=[ErrorExample(value="-5", row=3)],
                total_affected_rows=1,
            )
        ],
    )
    as_dict = result.to_dict()
    assert as_dict["summary"] == "One issue."
    assert as_dict["errors"][0]["errorType"] == "value_error"
    assert as_dict["errors"][0]["totalAffectedRows"] == 1
    assert as_dict["errors"][0]["examples"] == [{"value": "-5", "row": 3}]


# --- Data profile ---


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Carol", "David", "Eve"],
            "age": ["30", "25", "-1", "40", "33"],
            "date": [
                "2024-01-01",
                "01/02/2024",
                "2024-03-15",
                "March 4th 2024",
                "2024-04-20",
            ],
        }
    )


def test_profile_contains_required_keys(sample_df):
    profile = build_profile(sample_df, sample_size=3)
    for key in [
        "total_rows",
        "total_columns",
        "column_names",
        "columns_meta",
        "sample_csv",
        "sample_size",
    ]:
        assert key in profile


def test_profile_sample_size_capped_at_df_length():
    small_df = pd.DataFrame({"a": ["1", "2"]})
    profile = build_profile(small_df, sample_size=100)
    assert profile["sample_size"] == 2


def test_profile_columns_meta_keys(sample_df):
    profile = build_profile(sample_df)
    for col in ["name", "age", "date"]:
        meta = profile["columns_meta"][col]
        assert "unique_count" in meta
        assert "empty_count" in meta
        assert "sample_distinct_values" in meta


# --- Summary prompt ---


def test_summary_error_line_carries_offending_values():
    # Without concrete values the model can only restate "<type> in <column>",
    # which is what produced the useless column-listing summaries.
    error = ColumnError(
        column="student_id",
        error_type="format_inconsistency",
        description="Mixed identifier formats",
        examples=[
            ErrorExample(value="876", row=1),
            ErrorExample(value="ID876", row=2),
        ],
        total_affected_rows=2,
    )
    line = _format_error_for_summary(error)
    assert '"876"' in line
    assert '"ID876"' in line
    assert "Mixed identifier formats" in line


def test_summary_error_line_caps_examples():
    error = ColumnError(
        column="c",
        error_type="value_error",
        description="d",
        examples=[ErrorExample(value=f"v{i}", row=i) for i in range(10)],
        total_affected_rows=10,
    )
    line = _format_error_for_summary(error, max_examples=3)
    assert '"v3"' not in line
    assert line.count('"v') == 3


def test_summary_error_line_without_examples():
    error = ColumnError(
        column="c",
        error_type="value_error",
        description="d",
        examples=[],
        total_affected_rows=1,
    )
    assert "offending values" not in _format_error_for_summary(error)


# --- Executor ---


def test_extract_code_strips_markdown_fences():
    raw = "```python\nprint('hello')\n```"
    assert _extract_code(raw) == "print('hello')"


def test_extract_code_passthrough_when_no_fences():
    raw = "print('hello')"
    assert _extract_code(raw) == "print('hello')"


def test_execute_returns_empty_list_for_no_errors():
    script = "import json, sys\nprint(json.dumps([]))"
    assert execute_detection_script(script, SAMPLE_CSV) == []


def test_execute_returns_parsed_errors():
    errors_json = json.dumps(
        [
            {
                "column": "age",
                "error_type": "value_error",
                "description": "Negative ages",
                "examples": [{"value": "-5", "row": 3}],
                "total_affected_rows": 1,
            }
        ]
    )
    script = f"import sys\nprint({repr(errors_json)})"
    result = execute_detection_script(script, SAMPLE_CSV)
    assert len(result) == 1
    assert result[0]["column"] == "age"


def test_execute_raises_on_nonzero_exit():
    script = "import sys\nsys.exit(1)"
    with pytest.raises(RuntimeError, match="exited with code 1"):
        execute_detection_script(script, SAMPLE_CSV)


def test_execute_raises_on_invalid_json():
    script = "print('not valid json')"
    with pytest.raises(RuntimeError, match="invalid JSON"):
        execute_detection_script(script, SAMPLE_CSV)


def test_execute_error_includes_generated_script():
    # The temp file is unlinked before the error propagates, so the script must
    # be echoed into the message or the failing code is lost to the logs.
    script = "import sys\nraise SystemExit(1)  # marker-for-test"
    with pytest.raises(RuntimeError, match="marker-for-test"):
        execute_detection_script(script, SAMPLE_CSV)


def test_execute_handles_numpy_scalars_via_default_str():
    # Regression: a generated script emitting numpy int64 crashed on
    # json.dumps. The prompt now mandates int() casts plus default=str; this
    # asserts that contract survives the round-trip into ColumnError.
    script = (
        "import json, numpy as np\n"
        "errors = [{\n"
        "    'column': 'age',\n"
        "    'error_type': 'value_error',\n"
        "    'description': 'Negative ages',\n"
        "    'examples': [{'value': str(-5), 'row': np.int64(3)}],\n"
        "    'total_affected_rows': np.int64(1),\n"
        "}]\n"
        "print(json.dumps(errors, default=str))"
    )
    raw = execute_detection_script(script, SAMPLE_CSV)
    error = ColumnError(**raw[0])
    assert error.examples[0].row == 3
    assert error.total_affected_rows == 1


# --- Retries ---


@pytest.fixture
def no_sleep(monkeypatch):
    """Collapse the backoff so retry tests run instantly."""
    monkeypatch.setattr(dq_llm.time, "sleep", lambda _: None)


def test_with_retries_returns_after_transient_failure(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "3")
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise requests.exceptions.ConnectTimeout("connect timed out")
        return "ok"

    assert dq_llm.with_retries(flaky, "test op") == "ok"
    assert len(calls) == 3


def test_with_retries_reraises_after_last_attempt(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "2")
    calls = []

    def always_fails():
        calls.append(1)
        raise requests.exceptions.ConnectionError("host unreachable")

    with pytest.raises(requests.exceptions.ConnectionError):
        dq_llm.with_retries(always_fails, "test op")
    assert len(calls) == 2


def test_with_retries_sees_through_connector_runtime_error(monkeypatch, no_sleep):
    # CommonLLMConnector.chat re-raises SCAYLE failures as a plain RuntimeError.
    # Matching only the outermost type would treat every chat timeout as
    # permanent and skip the retry entirely.
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "3")
    calls = []

    def wrapped_timeout():
        calls.append(1)
        try:
            raise requests.exceptions.ReadTimeout("read timed out")
        except requests.exceptions.ReadTimeout as e:
            if len(calls) < 3:
                raise RuntimeError(f"Scayle chat error: {e}")
        return "ok"

    assert dq_llm.with_retries(wrapped_timeout, "chat completion") == "ok"
    assert len(calls) == 3


def test_with_retries_does_not_retry_wrapped_auth_error(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "3")
    calls = []

    def wrapped_auth_failure():
        calls.append(1)
        try:
            raise AuthenticationError(
                "invalid password", llm_provider="openai", model="qwen3"
            )
        except AuthenticationError as e:
            raise RuntimeError(f"Scayle chat error: {e}")

    with pytest.raises(RuntimeError):
        dq_llm.with_retries(wrapped_auth_failure, "chat completion")
    assert len(calls) == 1


def test_with_retries_does_not_retry_programming_errors(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "3")
    calls = []

    def bug():
        calls.append(1)
        raise RuntimeError("LLM returned an empty or unexpected response")

    with pytest.raises(RuntimeError):
        dq_llm.with_retries(bug, "chat completion")
    assert len(calls) == 1


def test_with_retries_does_not_retry_auth_errors(monkeypatch, no_sleep):
    # Bad credentials never recover, so retrying only delays the failure.
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "5")
    calls = []

    def bad_credentials():
        calls.append(1)
        raise AuthenticationError("invalid password", llm_provider="openai", model="qwen3")

    with pytest.raises(AuthenticationError):
        dq_llm.with_retries(bad_credentials, "test op")
    assert len(calls) == 1


def test_with_retries_single_attempt_when_disabled(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "1")
    calls = []

    def always_fails():
        calls.append(1)
        raise requests.exceptions.ConnectionError("host unreachable")

    with pytest.raises(requests.exceptions.ConnectionError):
        dq_llm.with_retries(always_fails, "test op")
    assert len(calls) == 1


@pytest.fixture(autouse=True)
def clear_cooldown():
    """The cool-off is process-global; keep it from leaking between tests."""
    dq_llm.reset_endpoint_cooldown()
    yield
    dq_llm.reset_endpoint_cooldown()


def test_endpoint_cooldown_short_circuits_after_setup_failure(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("DATA_QUALITY_LLM_COOLDOWN", "300")
    builds = []

    def unreachable():
        builds.append(1)
        raise requests.exceptions.ConnectTimeout("connect timed out")

    monkeypatch.setattr(dq_llm, "_build_llm_connector", unreachable)

    with pytest.raises(requests.exceptions.ConnectTimeout):
        dq_llm.get_llm_connector()
    assert len(builds) == 2  # both attempts used

    # The next table must not re-probe the dead endpoint at all.
    with pytest.raises(dq_llm.LLMEndpointUnavailable):
        dq_llm.get_llm_connector()
    assert len(builds) == 2


def test_endpoint_cooldown_can_be_disabled(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("DATA_QUALITY_LLM_COOLDOWN", "0")
    builds = []

    def unreachable():
        builds.append(1)
        raise requests.exceptions.ConnectTimeout("connect timed out")

    monkeypatch.setattr(dq_llm, "_build_llm_connector", unreachable)

    for _ in range(2):
        with pytest.raises(requests.exceptions.ConnectTimeout):
            dq_llm.get_llm_connector()
    assert len(builds) == 2


def test_successful_setup_clears_cooldown(monkeypatch, no_sleep):
    monkeypatch.setenv("DATA_QUALITY_LLM_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("DATA_QUALITY_LLM_COOLDOWN", "300")

    def unreachable():
        raise requests.exceptions.ConnectTimeout("connect timed out")

    monkeypatch.setattr(dq_llm, "_build_llm_connector", unreachable)
    with pytest.raises(requests.exceptions.ConnectTimeout):
        dq_llm.get_llm_connector()

    monkeypatch.setattr(dq_llm, "_build_llm_connector", lambda: "connector")
    dq_llm.reset_endpoint_cooldown()
    assert dq_llm.get_llm_connector() == "connector"
    # A later failure-free call stays unblocked.
    assert dq_llm.get_llm_connector() == "connector"


def test_scayle_auth_separates_connect_and_read_timeouts():
    # A scalar requests timeout also bounds the connect phase, so an
    # unreachable host would hang for the full read timeout.
    client = ScayleAuthClient(
        username="u", password="p", base_url="https://host/api", timeout=300.0
    )
    connect, read = client._request_timeout
    assert connect == ScayleAuthClient.DEFAULT_CONNECT_TIMEOUT
    assert read == 300.0


def test_scayle_auth_connect_timeout_never_exceeds_read_timeout():
    client = ScayleAuthClient(
        username="u", password="p", base_url="https://host/api", timeout=5.0
    )
    assert client._request_timeout == (5.0, 5.0)


# --- Gating ---


def test_data_quality_disabled_by_default(monkeypatch):
    # setenv, not delenv: cta.py calls load_dotenv() at import time, which
    # reinstates ENABLE_DATA_QUALITY from the developer's .env if the variable
    # is absent. Setting it explicitly wins, because load_dotenv does not
    # override variables that already exist.
    monkeypatch.setenv("ENABLE_DATA_QUALITY", "false")
    assert is_data_quality_enabled() is False


def test_data_quality_enabled_via_env(monkeypatch):
    monkeypatch.setenv("ENABLE_DATA_QUALITY", "true")
    assert is_data_quality_enabled() is True


# --- Full pipeline with a faked LLM (everything else runs for real) ---

FAKE_DETECTION_SCRIPT = """\
import json
import sys

import pandas as pd

df = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
errors = []
bad_ages = [
    (i + 1, v) for i, v in enumerate(df["age"]) if v.lstrip("-").isdigit() and int(v) < 0
]
if bad_ages:
    errors.append({
        "column": "age",
        "error_type": "value_error",
        "description": "Negative age values",
        "examples": [{"value": v, "row": r} for r, v in bad_ages[:5]],
        "total_affected_rows": len(bad_ages),
    })
print(json.dumps(errors))
"""


def test_detector_pipeline_with_fake_llm(monkeypatch):
    """Exercises profile building, script execution, and model validation;
    only the two LLM calls are faked."""
    from dataset_profiler.data_quality import detector, prompts

    class FakeConnector:
        provider = "scayle-llm"
        model = "kimi-k2.5"

    calls = []

    def fake_chat_completion(connector, messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:  # script generation call
            return FAKE_DETECTION_SCRIPT
        return "Detected value errors in the age column."

    monkeypatch.setattr(detector, "get_llm_connector", lambda: FakeConnector())
    monkeypatch.setattr(prompts, "chat_completion", fake_chat_completion)

    result = detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")

    assert result is not None
    assert len(result.errors) == 1
    assert result.errors[0].column == "age"
    assert result.errors[0].error_type == "value_error"
    assert result.errors[0].examples[0].value == "-5"
    assert "Negative ages" in calls[1][0]["content"] or "age" in calls[1][0]["content"]
    assert result.summary == "Detected value errors in the age column."


# --- CSVRecordSet integration ---


def test_csv_record_set_includes_data_quality(monkeypatch):
    # setenv, not delenv: cta.py calls load_dotenv() at import time, which
    # reinstates ENABLE_DATA_QUALITY from the developer's .env if the variable
    # is absent. Setting it explicitly wins, because load_dotenv does not
    # override variables that already exist.
    monkeypatch.setenv("ENABLE_DATA_QUALITY", "false")
    from dataset_profiler.profile_components.record_set.csv.csv_record_set import (
        CSVRecordSet,
    )

    record_set = CSVRecordSet(
        distribution_path=str(SAMPLE_CSV.parent),
        file_object="patients.csv",
        file_object_id="test-id",
    )
    # Disabled by default: no dataQuality section in the profile
    assert record_set.data_quality is None
    assert "dataQuality" not in record_set.to_dict()
    assert "data_quality" not in record_set.to_dict_cdd()

    # When a result is present it surfaces in the heavy MoMa profile only
    record_set.data_quality = DataQualityResult(
        summary="One issue.",
        errors=[
            ColumnError(
                column="age",
                error_type="value_error",
                description="Negative ages",
                examples=[ErrorExample(value="-5", row=3)],
                total_affected_rows=1,
            )
        ],
    )
    assert record_set.to_dict()["dataQuality"]["errors"][0]["errorType"] == "value_error"
    # The CDD profile never carries data quality, even when a result exists.
    assert "data_quality" not in record_set.to_dict_cdd()


# --- errorType is a closed set ---


def test_error_type_rejects_values_outside_the_documented_three():
    """The LLM invented "missing_value" in a real run; the schema publishes an
    enum, so the value set has to actually be closed."""
    from pydantic import ValidationError

    for bad in ("missing_value", "range_error", ""):
        with pytest.raises(ValidationError):
            ColumnError(
                column="c", error_type=bad, description="d",
                examples=[], total_affected_rows=1,
            )


def test_one_malformed_error_does_not_discard_the_whole_batch():
    """Detection failures are swallowed, so a batch-level raise would silently
    lose every finding for the record set."""
    from dataset_profiler.data_quality.detector import _validate_errors

    raw = [
        {"column": "a", "error_type": "value_error", "description": "d",
         "examples": [], "total_affected_rows": 1},
        {"column": "b", "error_type": "missing_value", "description": "d",
         "examples": [], "total_affected_rows": 1},
        {"column": "c", "error_type": "consistency_error", "description": "d",
         "examples": [], "total_affected_rows": 2},
    ]
    kept = _validate_errors(raw, "x.csv")
    assert [e.column for e in kept] == ["a", "c"]


# --- Column signals (computed over every row, not the sample) ---


def test_value_shape_keeps_digit_counts_but_collapses_letters():
    from dataset_profiler.data_quality.data_profile import value_shape

    assert value_shape("2025-03-01") == "9999-99-99"
    assert value_shape("01/03/2025") == "99/99/9999"
    assert value_shape("S2024-00123") == "A9999-99999"
    assert value_shape("Athens") == value_shape("Thessaloniki") == "Aa"
    assert value_shape("ATHENS") == "A"


def test_signals_expose_shape_split_with_exact_counts():
    from dataset_profiler.data_quality.data_profile import _column_signals

    col = pd.Series([f"2025-03-{d:02d}" for d in range(1, 31)] * 3 + ["01/03/2025"] * 7)
    signals = _column_signals(col)
    assert signals["kind"] == "text"
    assert signals["shapes"] == {"9999-99-99": 90, "99/99/9999": 7}


def test_signals_give_categorical_columns_full_counts_and_case_variants():
    from dataset_profiler.data_quality.data_profile import _column_signals

    col = pd.Series(["Athens"] * 20 + ["ATHENS"] * 3 + ["Athína"] * 2 + ["Patras"] * 10)
    signals = _column_signals(col)
    assert signals["kind"] == "categorical"
    assert signals["value_counts"]["Athína"] == 2  # visible even though sampling might miss it
    assert {"Athens": 20, "ATHENS": 3} in signals["case_variant_groups"]


def test_signals_report_numeric_range_and_negatives():
    from dataset_profiler.data_quality.data_profile import _column_signals

    col = pd.Series(["12.4", "-1.8", "30", "-999", "", "8"])
    signals = _column_signals(col)
    assert signals["kind"] == "numeric"
    assert signals["min"] == -999 and signals["negative_count"] == 2


# --- Findings are checked against the data before they are published ---


def _error(column, error_type, rows, examples=()):
    return ColumnError(
        column=column, error_type=error_type, description="d",
        examples=[ErrorExample(value=v, row=r) for v, r in examples],
        total_affected_rows=rows,
    )


@pytest.fixture
def status_df():
    # 90 rows in the dominant spelling, 10 deviating.
    return pd.DataFrame({"status": ["active"] * 90 + ["Active"] * 6 + ["ACTIVE"] * 4})


def test_inconsistency_counting_the_dominant_form_is_rejected(status_df):
    """A real run reported 310 of 520 rows for enrolment_status; only 52 deviated."""
    from dataset_profiler.data_quality.detector import _problem_with

    problem = _problem_with(_error("status", "consistency_error", 100, [("Active", 91)]), status_df)
    assert problem and "at most 50" in problem


def test_correctly_counted_inconsistency_passes(status_df):
    from dataset_profiler.data_quality.detector import _problem_with

    assert _problem_with(_error("status", "consistency_error", 10, [("Active", 91)]), status_df) is None


def test_bound_allows_a_genuine_split_with_no_majority_form():
    """40/30/30 across three spellings: 60 deviating rows is correct, not a miscount."""
    from dataset_profiler.data_quality.detector import _problem_with

    df = pd.DataFrame({"country": ["GR"] * 40 + ["Greece"] * 30 + ["greece"] * 30})
    assert _problem_with(_error("country", "consistency_error", 60, [("greece", 71)]), df) is None


def test_example_with_wrong_row_is_corrected_not_reported(status_df):
    from dataset_profiler.data_quality.detector import _problem_with

    error = _error("status", "consistency_error", 10, [("ACTIVE", 3)])  # row 3 holds "active"
    assert _problem_with(error, status_df) is None
    assert error.examples[0].row == 97


def test_examples_absent_from_the_column_are_reported(status_df):
    from dataset_profiler.data_quality.detector import _problem_with

    problem = _problem_with(_error("status", "consistency_error", 10, [("Enabled", 1)]), status_df)
    assert problem and "occur" in problem


def test_unknown_column_is_reported(status_df):
    from dataset_profiler.data_quality.detector import _problem_with

    assert "no such column" in _problem_with(_error("nope", "value_error", 1), status_df)


# --- Repair loop ---


CRASHING_SCRIPT = "import sys\nraise NameError(\"name 'eu_pattern' is not defined\")\n"

MISCOUNTING_SCRIPT = """\
import json, sys
import pandas as pd
df = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
print(json.dumps([{"column": "age", "error_type": "format_inconsistency",
    "description": "d", "examples": [{"value": df["age"][0], "row": 1}],
    "total_affected_rows": len(df)}]))
"""


def _fake_llm(monkeypatch, scripts):
    """Serve the given scripts to generation/repair calls, then a summary."""
    from dataset_profiler.data_quality import detector, prompts

    class FakeConnector:
        provider = "scayle-llm"
        model = "fake"

    calls = []

    def fake_chat_completion(connector, messages, **kwargs):
        calls.append(messages)
        is_script_request = messages[0]["role"] == "system"
        if is_script_request:
            return scripts[min(len([c for c in calls if c[0]["role"] == "system"]), len(scripts)) - 1]
        return "Detected value errors in the age column."

    monkeypatch.setattr(detector, "get_llm_connector", lambda: FakeConnector())
    monkeypatch.setattr(prompts, "chat_completion", fake_chat_completion)
    return calls


def test_crashing_script_is_repaired(monkeypatch):
    """A real run's script defined us_eu_pattern and then called eu_pattern."""
    from dataset_profiler.data_quality import detector

    calls = _fake_llm(monkeypatch, [CRASHING_SCRIPT, FAKE_DETECTION_SCRIPT])
    result = detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")

    assert result is not None and [e.column for e in result.errors] == ["age"]
    repair = calls[1]
    assert repair[-2] == {"role": "assistant", "content": CRASHING_SCRIPT}
    assert "eu_pattern" in repair[-1]["content"]


def test_miscounted_findings_are_sent_back_for_repair(monkeypatch):
    from dataset_profiler.data_quality import detector

    calls = _fake_llm(monkeypatch, [MISCOUNTING_SCRIPT, FAKE_DETECTION_SCRIPT])
    result = detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")

    assert "deviate from the column's dominant form" in calls[1][-1]["content"]
    assert [e.error_type for e in result.errors] == ["value_error"]


def test_persistently_failing_script_still_raises(monkeypatch):
    from dataset_profiler.data_quality import detector

    calls = _fake_llm(monkeypatch, [CRASHING_SCRIPT])
    with pytest.raises(RuntimeError, match="still failing"):
        detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")
    assert len(calls) == 1 + detector.MAX_REPAIR_ATTEMPTS


def test_findings_contradicting_the_data_are_dropped_once_repairs_run_out(monkeypatch):
    from dataset_profiler.data_quality import detector

    _fake_llm(monkeypatch, [MISCOUNTING_SCRIPT])
    result = detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")
    assert result.errors == []


# --- Repair feedback is specific enough to act on ---


def test_failure_excerpt_keeps_own_frames_and_whole_exception_but_drops_library_frames():
    """A real traceback was mostly pandas internals; the model rebuilt the same broken mask."""
    from dataset_profiler.data_quality.detector import _failure_excerpt

    tb = (
        "Detection script exited with code 1.\nstderr:\nTraceback (most recent call last):\n"
        '  File "/tmp/t.py", line 31, in main\n'
        "    affected = df[mask].index.tolist()\n"
        "               ~~^^^^^^\n"
        '  File "/usr/lib/python3.11/site-packages/pandas/core/indexes/base.py", line 6249, in _raise\n'
        '    raise KeyError(f"None of [{key}]")\n'
        'KeyError: "None of [Index([ None,  None, False,\n'
        "      dtype='object', length=600)] are in the [columns]\"\n"
        "\ngenerated script:\nimport pandas\n"
    )
    excerpt = _failure_excerpt(RuntimeError(tb))
    assert "df[mask]" in excerpt
    assert "length=600" in excerpt        # indented continuation of the exception survives
    assert "site-packages" not in excerpt
    assert "import pandas" not in excerpt  # the echoed script is not repeated


def test_combined_column_name_gets_actionable_message():
    """A real run named its finding 'systolic_bp,diastolic_bp' and was dropped for it."""
    from dataset_profiler.data_quality.detector import _problem_with

    df = pd.DataFrame({"systolic_bp": ["0", "120"], "diastolic_bp": ["69", "80"]})
    problem = _problem_with(_error("systolic_bp,diastolic_bp", "consistency_error", 1), df)
    assert "exactly one column name" in problem and "diastolic_bp" in problem


def test_examples_taken_from_another_column_are_named():
    from dataset_profiler.data_quality.detector import _problem_with

    df = pd.DataFrame({"systolic_bp": ["0", "120", "0"], "diastolic_bp": ["69", "80", "89"]})
    error = _error("systolic_bp", "value_error", 2, [("69", 1), ("89", 3)])
    problem = _problem_with(error, df)
    assert "come from column 'diastolic_bp'" in problem


# --- Example values are matched loosely, and never cost a real finding ---


def test_examples_match_despite_float_formatting_and_quotes():
    """Run 3 dropped every clinic finding: example values arrived formatted
    differently from the raw cells."""
    from dataset_profiler.data_quality.detector import _problem_with

    df = pd.DataFrame({"age": ["36", "-12", "142", "40"]})
    error = _error("age", "value_error", 2, [("-12.0", 2), ("'142'", 3)])
    assert _problem_with(error, df) is None
    assert [e.row for e in error.examples] == [2, 3]


def test_unmatched_example_message_shows_what_the_row_holds():
    from dataset_profiler.data_quality.detector import _problem_with

    df = pd.DataFrame({"age": ["36", "-12", "142"]})
    problem = _problem_with(_error("age", "value_error", 1, [("minus twelve", 2)]), df)
    assert "'minus twelve'" in problem and "row 2 holds '-12'" in problem


WRONG_EXAMPLES_SCRIPT = """\
import json, sys
import pandas as pd
df = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
bad = [v for v in df["age"] if v.lstrip("-").isdigit() and int(v) < 0]
print(json.dumps([{"column": "age", "error_type": "value_error",
    "description": "Negative ages", "examples": [{"value": "not-in-file", "row": 1}],
    "total_affected_rows": len(bad)}]))
"""


def test_finding_wrong_only_in_its_examples_survives_without_them(monkeypatch):
    from dataset_profiler.data_quality import detector

    _fake_llm(monkeypatch, [WRONG_EXAMPLES_SCRIPT])
    result = detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")
    assert [e.column for e in result.errors] == ["age"]
    assert result.errors[0].examples == []
