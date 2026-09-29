import argparse
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from litellm.types.utils import ModelResponse, Choices, Message, Usage

from dotenv import load_dotenv

load_dotenv()

import pandas as pd
from tqdm import tqdm

from dataset_profiler.common_llm import CommonLLMConnector
from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# SCAYLE model ids are case sensitive and drift over time. "Qwen3" used to work
# and now fails with HTTP 400 ("Model not found") — the endpoint serves the
# lowercase "qwen3" instead — just as both "gemma4" and "Gemma4" did before it.
# Because annotation failures are swallowed per column, a stale id silently
# writes "error" into every column while the job still reports success, so the
# id is overridable with CTA_LLM_MODEL: the next drift is a config change rather
# than a rebuild. qwen3 answers in the short form this prompt expects and is
# ~3x faster per column than qwen3.6, which matters at one call per column.
DEFAULT_CTA_MODEL = "qwen3"



def normalize_semantic_type(raw: str) -> str:
    """Put a model answer into one canonical form.

    The same model returns the same type as "attendance_percentage",
    "Attendance percentage." or '"attendance percentage"' from one run to the
    next, which makes identical annotations look different to anything matching
    on them. Only formatting is normalised; the wording itself is left alone.
    """
    lines = [line for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        return "unknown"
    text = lines[0]
    # "column_name: type" -- the model occasionally echoes the header first.
    if ":" in text:
        text = text.rsplit(":", 1)[1]
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip().strip("\"'`*.,;!?()[]{}").strip()
    return text.lower() or "unknown"


# Answers the model gives when a label would add nothing beyond the header.
NO_LABEL_ANSWERS = {"none", "null"}

# Words that add nothing when appended to a header: "phone number" for "phone",
# "email address" for "instructor_email", "grade value" for "grade".
FILLER_WORDS = {"number", "address", "name", "value"}


def _header_tokens(text: str) -> List[str]:
    """Lowercase words of a header or label: splits snake_case, camelCase, dashes and dots."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.split(r"[^0-9a-zA-Z\u00C0-\uFFFF]+", text.lower())
    # A trailing plural "s" is not a difference in meaning ("validations" / "validation").
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words if w]


def is_redundant_with_header(label: str, header: str) -> bool:
    """Whether a label only repeats the column header.

    "date" for "Date", "patient name" for "patient_name" and "boarding disembark"
    for "boarding_disembark_desc" say nothing the header does not: every word of
    the label is already in it. A label that expands or translates the header
    ("systolic blood pressure" for "systolic_bp", "municipality" for "Kommune")
    is kept.
    """
    label_words, header_words = _header_tokens(label), _header_tokens(header)
    if not label_words or not header_words:
        return False
    if "".join(label_words) == "".join(header_words):   # "datehour" vs "date hour"
        return True
    content = set(label_words) - FILLER_WORDS
    return bool(content) and content <= set(header_words)


def finalize_semantic_type(raw: str, header: str) -> Optional[str]:
    """Normalise a model answer, returning None when the label would add nothing.

    None is a deliberate "no label": the header already says what the column
    holds. It is kept apart from "unknown" (the model could not tell), "error"
    (the call failed) and "" (annotation did not run).
    """
    label = normalize_semantic_type(raw)
    if label in NO_LABEL_ANSWERS:
        return None
    if label not in ("unknown", "identifier") and is_redundant_with_header(label, header):
        return None
    return label


class ColumnTypeAnnotator:
    def __init__(
        self,
        # None means: CTA_LLM_MODEL if set, else DEFAULT_CTA_MODEL.
        model: Optional[str] = None,
        llm_provider: str = "scayle-llm",
        sample_size: int = 10,
    ):
        self.sample_size = sample_size
        self.model_name = model or os.environ.get("CTA_LLM_MODEL") or DEFAULT_CTA_MODEL
        self.llm_provider = llm_provider

        self.llm = CommonLLMConnector(
            provider=llm_provider,
            model=self.model_name,
            config_file="dataset_profiler/common_llm/configs/llm_config.yaml")

        self.system_message = self._get_system_message()

    @staticmethod
    def _get_system_message() -> str:
        return (
            "You are an expert Data Analyst specializing in Semantic Data Profiling. "
            "Your task is Column Type Annotation.\n\n"
            "GUIDELINES:\n"
            "1. Return your answer in 1 to max 3 words.\n"
            "2. Do NOT return structural data types (e.g., 'string', 'float').\n"
            "3. Be as exact and precise as possible.\n"
            "4. If the target column header best describes the column content, return that.\n"
            "5. If unknown, return: unknown\n"
            "6. No punctuation, quotes, or explanations.\n"
            "7. If the target column contains mostly unique identifiers, return 'identifier'.\n"
        )

    def _build_prompt(
        self,
        col: str,
        all_headers: List[str],
        samples: List[Any],
        semantic_types: Dict[str, str],
        extra_info: Optional[Sequence[Dict[str, Any]]] = None,
        labels: Optional[List[str]] = None,
    ) -> str:
        context_cols = [c for c in all_headers if c != col]
        prompt = f"<target_column_header>{col}</target_column_header>\n"
        prompt += f"<rest_headers>{context_cols}</rest_headers>\n"
        prompt += f"<sample_values>{samples}</sample_values>\n"
        if semantic_types:
            prompt += f"<previous_annotations>{semantic_types}</previous_annotations>\n"
        if extra_info is not None:
            prompt += f"<extra_info>{extra_info}</extra_info>\n"

        if labels and len(labels) > 0:
            prompt += f"<labels>{labels}</labels>\n"
            prompt += "The possible semantic types are listed in <labels>. Classify the target column into one of these types if possible. If it doesn't fit any, return 'unknown'.\n"
        else:
            prompt += "\nBased on the context columns and the sample values, what is the semantic type of the target column?\n"

        prompt += "Return your answer immediately after ANSWER:"

        return prompt

    def _parse_response(self, response: str) -> str:
        try:
            content = response.choices[0].message.content
            if "ANSWER:" in content:
                content = content.split("ANSWER:", 1)[1]
            return normalize_semantic_type(content)
        except Exception as e:
            logger.warning(f"Failed to parse response: {e}")
            return "unknown"

    def annotate_columns(
        self,
        df: Optional[pd.DataFrame] = None,
        db: Optional[DatagemsPostgres] = None,
        table_name: Optional[str] = None,
        columns_to_annotate: Optional[List[str]] = None,
        extra_info_df: Optional[pd.DataFrame] = None,
        show_progress: bool = False,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Optional[str]]:
        """Annotates all columns either of a DataFrame or of a specific table of a Database.

        A column maps to None when its header is already self-explanatory.
        """

        # In case of database columns annotation, fetch a subtable (100 first rows) of the target table
        if df is None:
            if db is None or table_name is None:
                raise ValueError("Either df or both db and table_name must be provided")
            try:
                query = f"SELECT * FROM {table_name} LIMIT 100;"
                result = db.execute(query)
                df = (
                    result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
                )
            except Exception as e:
                logger.error(f"Failed to annotate columns from database: {e}")
                return {col: "error" for col in (columns_to_annotate or [])}

        all_headers = df.columns.tolist()
        target_cols = [
            c for c in (columns_to_annotate or all_headers) if c in all_headers
        ]

        semantic_types = {}
        # The model's own answers, shown to it as <previous_annotations>. They
        # are kept apart from the output because feeding back the None of
        # dropped labels makes the model drift to vague labels ("monetary
        # amount" instead of "medical fee") for the columns that follow.
        answers = {}
        pbar = tqdm(
            target_cols,
            desc="Annotating columns",
            unit="col",
            disable=not show_progress,
        )

        for col in pbar:
            if show_progress:
                pbar.set_description(f"Annotating: '{col}'")

            valid_data = df[col].dropna()
            samples = (
                valid_data.sample(min(self.sample_size, len(valid_data))).tolist()
                if not valid_data.empty
                else []
            )
            extra_info = (
                extra_info_df.to_dict(orient="records")
                if extra_info_df is not None
                else None
            )

            messages = [
                {"role": "system", "content": self.system_message},
                {
                    "role": "user",
                    "content": self._build_prompt(
                        col, all_headers, samples, answers, extra_info, labels
                    ),
                },
            ]

            try:
                raw_response = self.llm.chat(messages, stream=False)
                # print("RAW_RESPONSE:", raw_response)
                answers[col] = self._parse_response(raw_response)
                semantic_types[col] = finalize_semantic_type(answers[col], col)
            except Exception as e:
                logger.error(f"Error for column '{col}': {e}")
                answers[col] = semantic_types[col] = "error"

        # Per-column errors above are swallowed so profiling still completes; log
        # one summary line so a dead or renamed model group is visible in the Ray
        # logs without having to read the resulting profile column by column.
        failed = [c for c, t in semantic_types.items() if t == "error"]
        if failed:
            logger.error(
                f"Semantic type annotation failed for {len(failed)}/{len(target_cols)} "
                f"columns with model '{self.model_name}' on provider "
                f"'{self.llm_provider}'; they are annotated as 'error'"
            )

        return semantic_types
