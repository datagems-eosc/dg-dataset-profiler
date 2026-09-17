import os
from pathlib import Path
from collections import Counter
from typing import List, Optional, Tuple, Union

import pandas as pd
from pydantic import ValidationError

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.data_quality.data_profile import build_profile, value_shape
from dataset_profiler.data_quality.executor import execute_detection_script
from dataset_profiler.data_quality.llm import get_llm_connector
from dataset_profiler.data_quality.models import ColumnError, DataQualityResult
from dataset_profiler.data_quality.prompts import (
    build_detection_messages,
    generate_detection_script,
    generate_summary,
    repair_detection_script,
)
from dataset_profiler.utilities import resolve_encoding

# Number of randomly sampled rows sent to the LLM as context.
SAMPLE_SIZE = 100
# Cap on reported example values per detected error.
MAX_EXAMPLES_PER_ERROR = 5
# Detection loads the whole file in memory (unlike the streamed statistics), so
# skip files larger than this to keep profiling memory bounded.
MAX_FILE_SIZE_MB = 100
# Further attempts at a usable script after the first one crashes or reports
# findings that contradict the data. Each attempt costs one LLM call.
MAX_REPAIR_ATTEMPTS = 2
# Longest excerpt of a failure passed back to the model when repairing.
MAX_PROBLEM_CHARS = 1500

INCONSISTENCY_TYPES = {"format_inconsistency", "consistency_error"}


def is_data_quality_enabled() -> bool:
    """Data quality detection is opt-in via the ENABLE_DATA_QUALITY env var."""
    return os.environ.get("ENABLE_DATA_QUALITY", "false").lower() in [
        "1",
        "true",
        "yes",
        "on",
    ]



def _validate_errors(raw_errors: list, file_path: Union[Path, str]) -> List[ColumnError]:
    """Turn the script's raw findings into ColumnErrors, dropping malformed ones.

    Validated one at a time rather than in a comprehension: a single entry the
    model got wrong -- most often an error_type outside the three it was asked
    for -- would otherwise fail the whole batch, and since detection failures are
    swallowed, that would silently discard every finding for the record set.
    """
    errors = []
    for raw in raw_errors:
        try:
            errors.append(ColumnError(**raw))
        except ValidationError as e:
            logger.warning(
                "Discarding malformed data quality error",
                file=str(file_path),
                column=raw.get("column"),
                error_type=raw.get("error_type"),
                reason=str(e).replace("\n", " ")[:200],
            )
    return errors



def _max_inconsistent_rows(values: pd.Series, error_type: str) -> int:
    """The most rows an inconsistency can plausibly affect in a column.

    An inconsistency is a deviation from the column's dominant form, so the rows
    in that form cannot be part of it. The bound is never below half the column,
    which keeps legitimate splits such as 40/30/30 across three spellings.
    """
    non_empty = values[values.str.strip() != ""]
    if non_empty.empty:
        return 0
    forms = non_empty.map(value_shape) if error_type == "format_inconsistency" else non_empty
    dominant = Counter(forms).most_common(1)[0][1]
    return max(len(non_empty) - dominant, len(non_empty) // 2)


def _problem_with(error: ColumnError, df: pd.DataFrame) -> Optional[str]:
    """Why a finding contradicts the data, or None if it holds up.

    Example rows that are merely wrong are corrected in place rather than
    reported: scripts disagree with the profiler about skipped malformed lines
    often enough that an off-by-a-few row number is not worth a repair.
    """
    if error.column not in df.columns:
        named = [c for c in df.columns if c in error.column]
        if named:
            return (
                f"'column' must be exactly one column name, not a combination of {named}. For a "
                "problem between columns, name the column holding the implausible value and take "
                "the examples from that column."
            )
        return "there is no such column in the file."
    values = df[error.column]
    n = error.total_affected_rows
    if n <= 0:
        return "total_affected_rows must be positive; omit findings that affect nothing."
    if n > len(df):
        return f"total_affected_rows is {n}, but the table only has {len(df)} rows."
    if error.error_type in INCONSISTENCY_TYPES:
        bound = _max_inconsistent_rows(values, error.error_type)
        if n > bound:
            return (
                f"reports {n} affected rows, but at most {bound} rows can deviate from the "
                "column's dominant form. Count only the deviating rows, and use deviating "
                "values as examples."
            )

    # Scripts quote values, or round-trip numbers through floats ("142.0" for
    # "142"), so examples are matched loosely rather than character for character.
    cells = values.str.strip().str.strip("'\"")
    numbers = pd.to_numeric(cells, errors="coerce")

    def rows_holding(value: str) -> List[int]:
        wanted = value.strip().strip("'\"")
        mask = cells == wanted
        number = pd.to_numeric(pd.Series([wanted]), errors="coerce").iloc[0]
        if pd.notna(number):
            mask = mask | (numbers == number)
        return [int(i) + 1 for i in mask[mask].index]

    used, kept = set(), []
    for example in error.examples:
        holding = rows_holding(example.value)
        if example.row in holding:
            chosen = example.row
        else:
            free = [r for r in holding if r not in used]
            if not free:
                continue
            chosen = free[0]
        example.row = chosen
        used.add(chosen)
        kept.append(example)
    if error.examples and not kept:
        wanted = {e.value.strip().strip("'\"") for e in error.examples}
        elsewhere = [c for c in df.columns if c != error.column
                     and wanted & set(df[c].str.strip())]
        if elsewhere:
            return (
                f"the example values come from column '{elsewhere[0]}', not '{error.column}'. "
                "Name the column the examples are taken from."
            )
        first = error.examples[0]
        actual = values.iloc[first.row - 1] if 1 <= first.row <= len(df) else None
        held = f" (row {first.row} holds {actual!r})" if actual is not None else ""
        return (
            f"none of the example values occur in that column: {first.value!r} is not there{held}. "
            "Examples must be raw cell values exactly as read with dtype=str."
        )
    error.examples = kept
    return None


def _check_errors(
    raw_errors: list, df: pd.DataFrame, file_path: Union[Path, str]
) -> Tuple[List[ColumnError], List[str], List[ColumnError]]:
    """Validate findings against the file itself.

    Returns three things: the findings that hold up; a description of each that
    does not, worded for the model so the list can be fed straight into a
    repair; and the findings whose *only* problem is their examples, stripped of
    them. Those are published if repairs run out -- a correct count with no
    usable examples is still a real finding, and dropping it cost a whole
    table's results in one run.
    """
    if not isinstance(raw_errors, list):
        return [], ["The script must print a JSON array of findings."], []
    kept, problems, examples_only = [], [], []
    for error in _validate_errors([e for e in raw_errors if isinstance(e, dict)], file_path):
        problem = _problem_with(error, df)
        if not problem:
            kept.append(error)
            continue
        problems.append(f"Column '{error.column}' ({error.error_type}): {problem}")
        stripped = error.model_copy(update={"examples": []})
        if _problem_with(stripped, df) is None:
            examples_only.append(stripped)
    return kept, problems, examples_only


def _failure_excerpt(exc: Exception) -> str:
    """The useful part of a script failure, for the model to act on.

    Library frames are dropped: a pandas traceback is mostly pandas internals,
    which bury the one frame from the model's own script and the final error
    line -- the two things it needs to fix the root cause rather than rebuild
    the same failing construct.
    """
    text = str(exc).split("generated script:")[0].strip()
    lines = text.splitlines()
    # The exception itself starts at the last unindented line and can wrap onto
    # indented continuation lines (pandas Index reprs do), so keep it whole.
    unindented = [i for i, line in enumerate(lines) if line and not line[0].isspace()]
    split = unindented[-1] if unindented else len(lines)
    lines, exception_block = lines[:split], lines[split:]
    kept, keep_next = [], False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('File "') and "site-packages" in stripped:
            keep_next = False
            continue
        if stripped.startswith('File "'):
            kept.append(line)
            keep_next = True
            continue
        if keep_next:
            if stripped and set(stripped) - set("~^ "):
                kept.append(line)
            keep_next = False
            continue
        if not line.startswith(" "):
            kept.append(line)
    return "\n".join(kept + exception_block)[-MAX_PROBLEM_CHARS:]


def detect_data_quality_errors(
    file_path: Union[Path, str],
    table_name: str,
    delimiter: str = ",",
    encoding: Optional[str] = None,
) -> Optional[DataQualityResult]:
    """Detect data quality errors in a tabular file (detection only, no correction).

    Sends a compact profile of the table to the LLM, which generates a Python
    detection script. The script is executed against the full file and its
    findings are summarised in a second LLM call.

    ``encoding`` defaults to whatever the file actually decodes as. It is
    threaded into the generated script too, so the script reads the file the
    same way this function does.

    Returns None when the file is empty or too large to analyze.
    """
    if encoding is None:
        encoding = resolve_encoding(file_path)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(
            "Skipping data quality detection: file exceeds size limit",
            file=str(file_path),
            file_size_mb=round(file_size_mb, 1),
            limit_mb=MAX_FILE_SIZE_MB,
        )
        return None

    # Read every column as string to preserve the original value formatting.
    df = pd.read_csv(
        file_path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
    )
    if df.empty:
        return None

    profile = build_profile(df, sample_size=SAMPLE_SIZE)
    connector = get_llm_connector()

    logger.info(
        "Generating data quality detection script",
        file=str(file_path),
        provider=connector.provider,
        model=connector.model,
    )
    messages = build_detection_messages(
        profile, delimiter=delimiter, encoding=encoding, max_examples=MAX_EXAMPLES_PER_ERROR
    )
    script_code = generate_detection_script(
        connector, profile, delimiter=delimiter, encoding=encoding,
        max_examples=MAX_EXAMPLES_PER_ERROR,
    )

    # The script is model-written, so it can crash, or run cleanly and still
    # report findings the data contradicts. Either way the model gets its own
    # script back with the failure and another attempt.
    errors: Optional[List[ColumnError]] = None
    problems: List[str] = []
    for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
        logger.info("Running data quality detection script", file=str(file_path), attempt=attempt)
        try:
            raw_errors = execute_detection_script(script_code, file_path)
        except RuntimeError as e:
            errors, problems, examples_only = None, [_failure_excerpt(e)], []
        else:
            errors, problems, examples_only = _check_errors(raw_errors, df, file_path)

        if not problems or attempt == MAX_REPAIR_ATTEMPTS:
            break
        logger.warning(
            "Repairing data quality detection script",
            file=str(file_path),
            attempt=attempt + 1,
            problems=[p[:200] for p in problems[:5]],
        )
        script_code = repair_detection_script(connector, messages, script_code, problems)

    if errors is None:
        raise RuntimeError(
            f"Detection script still failing after {MAX_REPAIR_ATTEMPTS} repairs: {problems[0]}"
        )
    if problems:
        # Out of attempts: publish what holds up rather than nothing, but never
        # a finding the data contradicts. Findings wrong only in their examples
        # are kept, without them.
        errors = errors + examples_only
        logger.warning(
            "Dropping data quality findings that contradict the data",
            file=str(file_path),
            problems=[p[:200] for p in problems[:5]],
        )

    summary = generate_summary(connector, errors, table_name, total_rows=len(df))

    logger.info(
        "Data quality detection finished",
        file=str(file_path),
        num_error_types=len(errors),
    )
    return DataQualityResult(summary=summary, errors=errors)
