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
4. `error_type` MUST be exactly one of those three values. Do not invent other categories
   — anything else is discarded. Conditional emptiness (a column empty only when another
   column is filled) is a consistency_error.
5. The column details above were computed over EVERY row, not the sample. Shapes, full value
   counts, case variants and numeric ranges with exact counts are all there — write checks for
   what they reveal rather than relying on the sample alone.
6. For format_inconsistency and consistency_error, first find the dominant form: the most
   frequent shape or spelling. Only rows that DEVIATE from it are affected. `total_affected_rows`
   counts those rows alone, and every example must be a deviating value, never the dominant form.
   Findings that count most of a column as inconsistent are rejected.
7. Do not report a format_inconsistency for a column whose values all share a single shape.
8. Do NOT report plainly missing or empty values as errors. Missing data is already counted
   per column as missingCount and missingPercentage, so repeating it here adds nothing.
9. `column` must be exactly ONE existing column name. For a problem involving two columns (a value
   that is impossible given another column), name the column holding the implausible value, take
   the examples from that column, and mention the other column in the description.
10. Values are strings and may be empty. Never call `float()` or `int()` on raw values: convert
    with `pd.to_numeric(df[col], errors="coerce")`. Build every boolean mask from comparisons or
    `.str` methods and finish it with `.fillna(False).astype(bool)` before indexing with it.
11. Every value you put in the JSON MUST be a built-in Python type, never a numpy or
   pandas scalar. Wrap every row number and count in `int(...)` and every erroneous
   value in `str(...)`. Pandas expressions such as `.index`, `.sum()`, `.nunique()`
   and `len(df[mask])` yield `numpy.int64`, which is NOT JSON serializable and will
   crash the script.
12. Print ONLY a valid JSON array to stdout (no other output whatsoever), serialized
    with `json.dumps(errors, default=str)`.
13. Row numbers are 1-indexed (first data row after header = row 1).
14. Include at most {max_examples} examples per error entry.
15. Output an empty array `[]` if no errors are found.
16. Only DETECT errors — do NOT attempt to correct or suggest fixes for any value.
17. Use only: pandas, re, json, sys, collections, datetime — no third-party packages.

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
Summarize the data quality issues detected in the table below.

Table: {table_name}
Total rows: {total_rows}
Errors found:
{errors_text}

Rules:
- Write 1 to 3 sentences, beginning with "Detected".
- Say what each issue actually IS, not merely that it exists. "Format
  inconsistencies in the student id column" is useless. "Student id mixes bare
  numbers with an 'ID'-prefixed form" is what is wanted.
- Quote concrete example values taken from the report above, in parentheses,
  to show the reader the actual problem.
- Do NOT recite every affected column. When many columns share one pattern,
  describe the pattern once and name two or three columns as examples.
- Report only what was detected. No severity ratings ("significant", "major",
  "mostly clean"), no impact or consequences ("compromising data integrity"),
  no recommendations.

Required style:
Detected mixed identifier formats in student id and question id, where bare \
numbers ("876") appear alongside prefixed values ("ID876"), and inconsistent \
casing in student country ("portugal" vs "Portugal").

Output only the summary, nothing else.\
"""

NO_ERRORS_SUMMARY = "No data quality errors were detected."


def _format_counts(counts: dict) -> str:
    return ", ".join(f'"{k}"={v}' for k, v in counts.items())


def _format_column_details(columns_meta: dict) -> str:
    lines = []
    for col, meta in columns_meta.items():
        signals = meta.get("signals") or {}
        kind = signals.get("kind")
        head = f"- {col}: {meta['unique_count']} unique values, {meta['empty_count']} empty."

        if kind == "numeric":
            head += (f" Numeric: min {signals['min']:g}, max {signals['max']:g}, "
                     f"{signals['negative_count']} negative.")
            if signals.get("non_numeric_values"):
                head += f" Non-numeric entries: {_format_counts(signals['non_numeric_values'])}."
            lines.append(head)
            continue

        if kind == "categorical":
            lines.append(head)
            lines.append(f"    all values: {_format_counts(signals['value_counts'])}")
        else:
            sample_vals = ", ".join(f'"{v}"' for v in meta["sample_distinct_values"][:10])
            lines.append(f"{head} Sample: [{sample_vals}]")
            if signals.get("shapes"):
                more = signals["shape_count"] - len(signals["shapes"])
                tail = f" (+{more} more shapes)" if more > 0 else ""
                lines.append(f"    shapes (9=digit, A/a=letters): {_format_counts(signals['shapes'])}{tail}")

        for group in signals.get("case_variant_groups", []):
            lines.append(f"    same value, different case/accents: {_format_counts(group)}")
    return "\n".join(lines)


def _format_error_for_summary(error: ColumnError, max_examples: int = 3) -> str:
    """Render one detected error for the summary prompt.

    The example values are the only concrete material the model has to write a
    specific summary with; without them it can do no better than restate the
    error type and column name.
    """
    line = (
        f"- Column '{error.column}' ({error.error_type}): {error.description} "
        f"[{error.total_affected_rows} rows affected]"
    )
    if error.examples:
        values = ", ".join(f'"{ex.value}"' for ex in error.examples[:max_examples])
        line += f"\n  offending values: {values}"
    return line


REPAIR_TEMPLATE = """\
Your script did not produce usable results:

{problems}

Fix the root cause named in the last line of each error — do not rebuild the same construct
that failed. Return the complete corrected script. Keep the checks that were working and still
follow every original requirement. Output ONLY the Python script.\
"""


def build_detection_messages(
    profile: dict,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    max_examples: int = 5,
) -> List[dict]:
    """The conversation that asks for a detection script.

    Kept separate from the call itself so a repair attempt can continue the
    same conversation instead of starting over without context.
    """
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
    return [
        {"role": "system", "content": SCRIPT_GENERATION_SYSTEM},
        {"role": "user", "content": prompt},
    ]


def generate_detection_script(
    connector: CommonLLMConnector,
    profile: dict,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    max_examples: int = 5,
) -> str:
    messages = build_detection_messages(profile, delimiter, encoding, max_examples)
    return chat_completion(connector, messages)


def repair_detection_script(
    connector: CommonLLMConnector,
    messages: List[dict],
    previous_script: str,
    problems: List[str],
) -> str:
    """Ask for a corrected script, showing the model its own script and what went wrong."""
    conversation = messages + [
        {"role": "assistant", "content": previous_script},
        {"role": "user", "content": REPAIR_TEMPLATE.format(
            problems="\n".join(f"- {p}" for p in problems)
        )},
    ]
    return chat_completion(connector, conversation)


def generate_summary(
    connector: CommonLLMConnector,
    errors: List[ColumnError],
    table_name: str,
    total_rows: int,
) -> str:
    if not errors:
        return NO_ERRORS_SUMMARY

    errors_text = "\n".join(_format_error_for_summary(e) for e in errors)
    prompt = SUMMARY_TEMPLATE.format(
        table_name=table_name,
        total_rows=total_rows,
        errors_text=errors_text,
    )
    messages = [{"role": "user", "content": prompt}]
    return chat_completion(connector, messages).strip()
