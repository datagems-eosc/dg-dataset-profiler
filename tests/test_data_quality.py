import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

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


# --- Gating ---


def test_data_quality_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_DATA_QUALITY", raising=False)
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
        return "The dataset is mostly clean. Negative ages affect one row."

    monkeypatch.setattr(detector, "get_llm_connector", lambda: FakeConnector())
    monkeypatch.setattr(prompts, "chat_completion", fake_chat_completion)

    result = detector.detect_data_quality_errors(SAMPLE_CSV, table_name="patients")

    assert result is not None
    assert len(result.errors) == 1
    assert result.errors[0].column == "age"
    assert result.errors[0].error_type == "value_error"
    assert result.errors[0].examples[0].value == "-5"
    assert "Negative ages" in calls[1][0]["content"] or "age" in calls[1][0]["content"]
    assert result.summary.startswith("The dataset is mostly clean.")


# --- CSVRecordSet integration ---


def test_csv_record_set_includes_data_quality(monkeypatch):
    monkeypatch.delenv("ENABLE_DATA_QUALITY", raising=False)
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

    # When a result is present, both profile flavours expose it
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
    assert (
        record_set.to_dict_cdd()["data_quality"]["errors"][0]["error_type"]
        == "value_error"
    )
