from typing import List

from dataset_profiler.common_llm.connector import CommonLLMConnector
from dataset_profiler.data_quality.llm import chat_completion
from dataset_profiler.data_quality.models import ColumnError

SCRIPT_GENERATION_SYSTEM = (
    "You are a data quality expert who writes precise, runnable Python scripts. "
    "You output ONLY valid Python code — no markdown, no explanations."
)

SCRIPT_GENERATION_TEMPLATE = """\
Generate a Python script to detect data quality errors in a dataset.

## Dataset profile
- Total rows: {total_rows}
- Columns: {column_names}

## Column details
{column_details}

## Randomly sampled rows ({sample_size} of {total_rows}):
{sample_csv}

## Script requirements
1. Read the full CSV file from `sys.argv[1]` with pandas, using `sep={delimiter!r}` and `encoding={encoding!r}`.
2. Read ALL columns as strings (`dtype=str, keep_default_na=False`) to preserve original formatting.
3. Detect errors of these types across ALL columns:
   - **format_inconsistency**: mixed date formats, mixed phone formats, inconsistent patterns
   - **value_error**: impossible/out-of-range values (negative ages, humidity > 100%, year 9999, etc.)
   - **consistency_error**: same concept with multiple representations ("english"/"en"/"English")
4. Print ONLY a valid JSON array to stdout (no other output whatsoever).
5. Row numbers are 1-indexed (first data row after header = row 1).
6. Include at most {max_examples} examples per error entry.
7. Output an empty array `[]` if no errors are found.
8. Only DETECT errors — do NOT attempt to correct or suggest fixes for any value.
9. Use only: pandas, re, json, sys, collections, datetime — no third-party packages.

## Required JSON output schema
[
  {{
    "column": "<column_name>",
    "error_type": "format_inconsistency|value_error|consistency_error",
    "description": "<clear human-readable description of the error pattern>",
    "examples": [
      {{"value": "<erroneous_value>", "row": <1-indexed row number>}}
    ],
    "total_affected_rows": <integer>
  }}
]

Output ONLY the Python script. No markdown fences, no explanation.\
"""

SUMMARY_TEMPLATE = """\
You are a data quality analyst. Write a 2-sentence summary of the following error report.

Table: {table_name}
Total rows: {total_rows}
Errors found:
{errors_text}

Sentence 1: Overall assessment of the dataset's data quality.
Sentence 2: The most critical issue(s) found and their impact.

Output exactly 2 sentences, nothing else.\
"""

NO_ERRORS_SUMMARY = (
    "No data quality errors were detected in this dataset. "
    "The data appears clean and consistent."
)


def _format_column_details(columns_meta: dict) -> str:
    lines = []
    for col, meta in columns_meta.items():
        sample_vals = ", ".join(f'"{v}"' for v in meta["sample_distinct_values"][:10])
        lines.append(
            f"- {col}: {meta['unique_count']} unique values, "
            f"{meta['empty_count']} empty. Sample: [{sample_vals}]"
        )
    return "\n".join(lines)


def generate_detection_script(
    connector: CommonLLMConnector,
    profile: dict,
    delimiter: str = ",",
    encoding: str = "ISO-8859-1",
    max_examples: int = 5,
) -> str:
    prompt = SCRIPT_GENERATION_TEMPLATE.format(
        total_rows=profile["total_rows"],
        column_names=", ".join(profile["column_names"]),
        column_details=_format_column_details(profile["columns_meta"]),
        sample_size=profile["sample_size"],
        sample_csv=profile["sample_csv"],
        delimiter=delimiter,
        encoding=encoding,
        max_examples=max_examples,
    )
    messages = [
        {"role": "system", "content": SCRIPT_GENERATION_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    return chat_completion(connector, messages)


def generate_summary(
    connector: CommonLLMConnector,
    errors: List[ColumnError],
    table_name: str,
    total_rows: int,
) -> str:
    if not errors:
        return NO_ERRORS_SUMMARY

    errors_text = "\n".join(
        f"- Column '{e.column}' ({e.error_type}): {e.description} "
        f"[{e.total_affected_rows} rows affected]"
        for e in errors
    )
    prompt = SUMMARY_TEMPLATE.format(
        table_name=table_name,
        total_rows=total_rows,
        errors_text=errors_text,
    )
    messages = [{"role": "user", "content": prompt}]
    return chat_completion(connector, messages).strip()
