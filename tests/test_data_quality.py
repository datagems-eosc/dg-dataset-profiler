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
