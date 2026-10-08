"""Keywords and a summary for document record sets (PDF and plain text).

One SCAYLE call per document returns both, so a PDF costs a single request.
Every failure is logged and degrades to empty keywords and an empty summary:
a document that cannot be described must not fail the whole profiling job.
"""

import json
import os
import re

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

MAX_KEYWORDS = 8
MAX_SUMMARY_WORDS = 150

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


def _build_connector() -> CommonLLMConnector:
    # No config_file on purpose: llm_config.yaml pins a 30s scayle timeout that
    # would override ours. The connector falls back to the SCAYLE_* env vars.
    return CommonLLMConnector(
        provider="scayle-llm",
        model=os.environ.get("DOCUMENT_LLM_MODEL") or DEFAULT_DOCUMENT_MODEL,
        scayle_timeout=float(
            os.environ.get("DOCUMENT_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)
        ),
    )


def _call_llm(prompt: str) -> str:
    """Send one prompt to SCAYLE and return the raw answer text."""
    response = _build_connector().chat(
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

    truncated = len(text) > MAX_INPUT_CHARS
    prompt = PROMPT.format(
        max_keywords=MAX_KEYWORDS,
        max_words=MAX_SUMMARY_WORDS,
        text=text[:MAX_INPUT_CHARS],
    )
    try:
        description = parse_description(_call_llm(prompt))
    except Exception as e:  # noqa: BLE001 - logged, never raised
        logger.error(
            "Document keyword and summary extraction failed",
            document=name,
            error_type=type(e).__name__,
            error=str(e)[:500],
        )
        return DocumentDescription()

    logger.info(
        "Described document",
        document=name,
        num_keywords=len(description.keywords),
        summary_words=len(description.summary.split()),
        truncated=truncated,
    )
    return description
