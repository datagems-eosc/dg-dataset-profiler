import os
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.data_quality.data_profile import build_profile
from dataset_profiler.data_quality.executor import execute_detection_script
from dataset_profiler.data_quality.llm import get_llm_connector
from dataset_profiler.data_quality.models import ColumnError, DataQualityResult
from dataset_profiler.data_quality.prompts import (
    generate_detection_script,
    generate_summary,
)

# Number of randomly sampled rows sent to the LLM as context.
SAMPLE_SIZE = 100
# Cap on reported example values per detected error.
MAX_EXAMPLES_PER_ERROR = 5
# Detection loads the whole file in memory (unlike the streamed statistics), so
# skip files larger than this to keep profiling memory bounded.
MAX_FILE_SIZE_MB = 100


def is_data_quality_enabled() -> bool:
    """Data quality detection is opt-in via the ENABLE_DATA_QUALITY env var."""
    return os.environ.get("ENABLE_DATA_QUALITY", "false").lower() in [
        "1",
        "true",
        "yes",
        "on",
    ]


def detect_data_quality_errors(
    file_path: Union[Path, str],
    table_name: str,
    delimiter: str = ",",
    encoding: str = "ISO-8859-1",
) -> Optional[DataQualityResult]:
    """Detect data quality errors in a tabular file (detection only, no correction).

    Sends a compact profile of the table to the LLM, which generates a Python
    detection script. The script is executed against the full file and its
    findings are summarised in a second LLM call.

    Returns None when the file is empty or too large to analyze.
    """
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
    script_code = generate_detection_script(
        connector,
        profile,
        delimiter=delimiter,
        encoding=encoding,
        max_examples=MAX_EXAMPLES_PER_ERROR,
    )

    logger.info("Running data quality detection script", file=str(file_path))
    raw_errors = execute_detection_script(script_code, file_path)
    errors = [ColumnError(**error) for error in raw_errors]

    summary = generate_summary(connector, errors, table_name, total_rows=len(df))

    logger.info(
        "Data quality detection finished",
        file=str(file_path),
        num_error_types=len(errors),
    )
    return DataQualityResult(summary=summary, errors=errors)
