"""Keywords and a summary for document record sets (PDF, plain text and JSON).

One SCAYLE call per document returns both, so a PDF costs a single request.
Every failure is logged and degrades to empty keywords and an empty summary:
a document that cannot be described must not fail the whole profiling job.

A profiling job can cap the total time its documents wait on the LLM with
``document_llm_time_budget``. Once the budget is spent, the remaining documents
get empty keywords and summaries, so a dataset of thousands of PDFs, or a slow
SCAYLE, cannot hold a job for hours.
"""

import json
import os
import re
import threading
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from pydantic import BaseModel, Field

from dataset_profiler.common_llm.connector import CommonLLMConnector
from dataset_profiler.configs.config_logging import logger

# SCAYLE model ids are case sensitive and drift over time, so the id is
# overridable with DOCUMENT_LLM_MODEL. qwen3.8-flash-next answered this prompt
# in ~2-4s per document on the IPB course offering, against ~6-8s for qwen3.
DEFAULT_DOCUMENT_MODEL = "qwen3.8-flash-next"
DEFAULT_TIMEOUT_SECONDS = 120.0

# Upper bound on the document text sent to the model. Course sheets and MathE
# material fit whole; longer documents are described from their beginning,
# which is where the title, abstract and table of contents live.
MAX_INPUT_CHARS = 24_000

# Below this many words there is nothing to describe, and the model invents
# keywords like "placeholder" or "empty document" instead.
MIN_INPUT_WORDS = 10

MAX_KEYWORDS = 5
MAX_SUMMARY_WORDS = 150

# Total time the documents of one profiling job may spend waiting on the LLM
# (DOCUMENT_LLM_TIME_BUDGET_SECONDS; 0 or less means no budget).
DEFAULT_TIME_BUDGET_SECONDS = 600.0

# A call that would get less time than this is not worth starting.
MIN_CALL_SECONDS = 5.0

PROMPT = """Describe the document below for a dataset catalogue.

Return:
- "keywords": up to {max_keywords} concise keywords or key phrases naming the main topics, methods or entities of the document.
- "summary": a summary of at most {max_words} words capturing the purpose and main content of the document.

Write both in the language of the document.

Document:
{text}

Answer with strict JSON only, no other text:
{{"keywords": ["keyword1", "keyword2"], "summary": "..."}}"""


class DocumentDescription(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""


def is_document_llm_enabled() -> bool:
    """Keywords and summaries are on by default; ENABLE_DOCUMENT_LLM=false turns them off."""
    return os.environ.get("ENABLE_DOCUMENT_LLM", "true").lower() in [
        "1",
        "true",
        "yes",
        "on",
    ]


def call_timeout_seconds() -> float:
    return float(os.environ.get("DOCUMENT_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))


def time_budget_seconds() -> float:
    return float(os.environ.get("DOCUMENT_LLM_TIME_BUDGET_SECONDS", DEFAULT_TIME_BUDGET_SECONDS))


class LLMTimeBudget:
    """LLM time left for the documents of one profiling job."""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.spent = 0.0
        self.skipped_documents = 0
        self._lock = threading.Lock()

    def remaining(self) -> float:
        with self._lock:
            return self.seconds - self.spent

    def charge(self, seconds: float) -> None:
        with self._lock:
            self.spent += seconds

    def skip(self) -> None:
        with self._lock:
            self.skipped_documents += 1


_active_budget: Optional[LLMTimeBudget] = None


@contextmanager
def document_llm_time_budget(seconds: Optional[float] = None) -> Iterator[Optional[LLMTimeBudget]]:
    """Cap the LLM time of every describe_document call made inside the block.

    ``seconds`` defaults to DOCUMENT_LLM_TIME_BUDGET_SECONDS; 0 or less means
    no cap. A module-level budget, not a context variable, so that documents
    described from worker threads share it too.
    """
    global _active_budget
    seconds = time_budget_seconds() if seconds is None else seconds
    if seconds <= 0:
        yield None
        return

    budget = LLMTimeBudget(seconds)
    previous, _active_budget = _active_budget, budget
    try:
        yield budget
    finally:
        _active_budget = previous
        if budget.skipped_documents:
            logger.warning(
                "Document LLM time budget ran out, later documents have no keywords or summary",
                budget_seconds=seconds,
                spent_seconds=round(budget.spent, 1),
                skipped_documents=budget.skipped_documents,
            )


def _build_connector(timeout: float) -> CommonLLMConnector:
    # No config_file on purpose: llm_config.yaml pins a 30s scayle timeout that
    # would override ours. The connector falls back to the SCAYLE_* env vars.
    return CommonLLMConnector(
        provider="scayle-llm",
        model=os.environ.get("DOCUMENT_LLM_MODEL") or DEFAULT_DOCUMENT_MODEL,
        scayle_timeout=timeout,
    )


def _call_llm(prompt: str, timeout: float) -> str:
    """Send one prompt to SCAYLE and return the raw answer text."""
    response = _build_connector(timeout).chat(
        message=[{"role": "user", "content": prompt}], stream=False, temperature=0.2
    )
    return response.choices[0].message.content or ""  # type: ignore[union-attr]


def parse_description(raw: str) -> DocumentDescription:
    """Read the model answer, tolerating ```json fences and text around the object."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        raise ValueError("no JSON object in the model answer")
    data = json.loads(match.group(0))
    keywords = [str(k).strip() for k in data.get("keywords") or [] if str(k).strip()]
    # Case-insensitive de-duplication, keeping the model's order.
    seen = set()
    keywords = [k for k in keywords if not (k.lower() in seen or seen.add(k.lower()))]
    return DocumentDescription(
        keywords=keywords[:MAX_KEYWORDS],
        summary=str(data.get("summary") or "").strip(),
    )


def describe_document(text: str, name: str | None = None) -> DocumentDescription:
    """Keywords and summary for one document, or an empty description on any failure."""
    if not is_document_llm_enabled():
        return DocumentDescription()

    text = text.strip()
    if len(text.split()) < MIN_INPUT_WORDS:
        logger.warning(
            "Document has too little extractable text, skipping keywords and summary",
            document=name,
            num_words=len(text.split()),
        )
        return DocumentDescription()

    timeout = call_timeout_seconds()
    budget = _active_budget
    if budget is not None:
        remaining = budget.remaining()
        if remaining < MIN_CALL_SECONDS:
            budget.skip()
            logger.info("Document LLM time budget spent, skipping keywords and summary",
                        document=name)
            return DocumentDescription()
        timeout = min(timeout, remaining)

    truncated = len(text) > MAX_INPUT_CHARS
    prompt = PROMPT.format(
        max_keywords=MAX_KEYWORDS,
        max_words=MAX_SUMMARY_WORDS,
        text=text[:MAX_INPUT_CHARS],
    )
    started = time.monotonic()
    try:
        description = parse_description(_call_llm(prompt, timeout=timeout))
    except Exception as e:  # noqa: BLE001 - logged, never raised
        logger.error(
            "Document keyword and summary extraction failed",
            document=name,
            error_type=type(e).__name__,
            error=str(e)[:500],
        )
        return DocumentDescription()
    finally:
        if budget is not None:
            budget.charge(time.monotonic() - started)

    logger.info(
        "Described document",
        document=name,
        num_keywords=len(description.keywords),
        summary_words=len(description.summary.split()),
        truncated=truncated,
    )
    return description
