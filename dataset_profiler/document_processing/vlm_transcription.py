"""Page-by-page transcription of documents with a SCAYLE vision model.

The "Pure VLM" pipeline of the PDF-to-Markdown benchmark gave the best
downstream quality on the MathE corpus: every page is rendered to an image and
transcribed to Markdown with LaTeX. This is the heavy path, used only by the
MathE document endpoints, never by the profiling pipeline.

Model choice (tested on SCAYLE 2026-11-23 on MathE pages): glm-5.3-flash keeps
annotations and describes figures, at 2.5-12s per page; qwen3.6 is faster
(1.4-5.4s) but drops more. kimi-k2.6 spends its whole budget reasoning, and the
other served models do not accept images. Turning glm's reasoning off breaks
it (the reasoning leaks into the answer), so it stays on.
"""

import base64
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from dataset_profiler.common_llm.connector import CommonLLMConnector
from dataset_profiler.configs.config_logging import logger
from dataset_profiler.document_processing.light_extraction import clean_markdown

DEFAULT_VLM_MODEL = "glm-5.3-flash"
DEFAULT_DPI = 150
# glm reasons before answering: a dense page used ~3,500 completion tokens.
DEFAULT_MAX_TOKENS = 8000
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_MAX_ATTEMPTS = 2

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
TEXT_SUFFIXES = {".txt", ".md"}
SUPPORTED_SUFFIXES = {".pdf", *IMAGE_MIME_TYPES, *TEXT_SUFFIXES}

# The benchmark's page_transcription prompt, with figures described in place
# instead of linked: the endpoint returns text only, no image files.
PAGE_PROMPT = """You are an expert document transcriber. Transcribe this document page into high-quality Markdown.
Follow these strict formatting rules:
1. Multi-column text: Follow natural human reading order across columns.
2. Mathematics: Convert all mathematical equations and formulas to standard LaTeX syntax ($...$ for inline math, $$...$$ for display equations).
3. Tables: Format tables using standard Markdown table syntax.
4. Figures & Charts: Where figures, plots, or diagrams appear, write a concise 2-sentence description in italics, starting with "Figure:", in place of the figure.
5. Annotations: Keep callouts, side notes and boxed remarks, next to the content they annotate.
6. Headings & Structure: Retain all sections, headings, bullet lists, and footnotes faithfully.
7. Return ONLY the Markdown content. Do not include introductory text or meta commentary."""


class UnsupportedDocumentError(ValueError):
    """The file type cannot be converted."""


class TranscriptionError(RuntimeError):
    """The vision model could not transcribe the document."""


@dataclass
class Transcription:
    markdown: str
    pages: int
    model: str
    # Pages the model could not transcribe; they hold the PDF's text layer.
    fallback_pages: list[int] = field(default_factory=list)


def vlm_model() -> str:
    return os.environ.get("DOCUMENT_VLM_MODEL") or DEFAULT_VLM_MODEL


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


def _build_connector(model: str) -> CommonLLMConnector:
    # No config_file: llm_config.yaml pins a 30s timeout, too short for a page.
    return CommonLLMConnector(
        provider="scayle-llm",
        model=model,
        scayle_timeout=_env_float("DOCUMENT_VLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS),
    )


def strip_outer_fence(content: str) -> str:
    """Remove a ```markdown fence wrapped around the whole answer."""
    content = content.strip()
    match = re.fullmatch(r"```[A-Za-z]*\n(.*)\n```", content, re.DOTALL)
    return match.group(1).strip() if match else content


def _transcribe_image(connector: CommonLLMConnector, image: bytes, mime: str) -> str:
    data_url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    response = connector.chat(
        message=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PAGE_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        stream=False,
        temperature=0,
        max_tokens=_env_int("DOCUMENT_VLM_MAX_TOKENS", DEFAULT_MAX_TOKENS),
    )
    choice = response.choices[0]  # type: ignore[union-attr]
    content = strip_outer_fence(choice.message.content or "")
    if not content:
        # glm and kimi answer empty when their reasoning hits max_tokens.
        raise RuntimeError(f"empty transcription (finish_reason={choice.finish_reason})")
    return content


def _transcribe_with_retries(connector, image: bytes, mime: str, label: str) -> str | None:
    attempts = _env_int("DOCUMENT_VLM_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)
    for attempt in range(1, attempts + 1):
        try:
            return _transcribe_image(connector, image, mime)
        except Exception as e:  # noqa: BLE001 - retried, then logged
            logger.warning("Page transcription failed", page=label, attempt=attempt,
                           max_attempts=attempts, error=str(e)[:300])
    return None


def _render_pages(pdf_path: str, dpi: int) -> tuple[list[bytes], list[str]]:
    with pymupdf.open(pdf_path) as doc:
        images = [page.get_pixmap(dpi=dpi).tobytes("png") for page in doc]
        layers = [page.get_text() for page in doc]
    return images, layers


def transcribe_document(path: str) -> Transcription:
    """Markdown of a PDF, an image or a text file.

    PDF pages are transcribed in parallel (DOCUMENT_VLM_MAX_CONCURRENCY). A page
    the model fails on keeps its text layer and is listed in fallback_pages; the
    call fails only when every page failed. Text files are returned as they are.
    """
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedDocumentError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )
    model = vlm_model()

    if suffix in TEXT_SUFFIXES:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return Transcription(markdown=text.strip(), pages=1, model="")

    connector = _build_connector(model)
    if suffix in IMAGE_MIME_TYPES:
        content = _transcribe_with_retries(connector, Path(path).read_bytes(),
                                           IMAGE_MIME_TYPES[suffix], label="1")
        if content is None:
            raise TranscriptionError("The vision model could not transcribe the image")
        return Transcription(markdown=content, pages=1, model=model)

    images, layers = _render_pages(path, _env_int("DOCUMENT_VLM_DPI", DEFAULT_DPI))
    if not images:
        return Transcription(markdown="", pages=0, model=model)

    workers = max(1, min(_env_int("DOCUMENT_VLM_MAX_CONCURRENCY", DEFAULT_MAX_CONCURRENCY),
                         len(images)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(
            lambda numbered: _transcribe_with_retries(connector, numbered[1], "image/png",
                                                      label=str(numbered[0])),
            enumerate(images, start=1),
        ))

    fallback_pages = [number for number, result in enumerate(results, start=1) if result is None]
    if len(fallback_pages) == len(images):
        raise TranscriptionError("The vision model could not transcribe any page")
    if fallback_pages:
        logger.warning("Pages kept their text layer after failed transcription",
                       path=path, pages=fallback_pages)

    pages = [result if result is not None else clean_markdown(layer)
             for result, layer in zip(results, layers)]
    logger.info("Transcribed document", path=path, pages=len(pages), model=model,
                fallback_pages=fallback_pages)
    return Transcription(
        markdown="\n\n".join(page for page in pages if page),
        pages=len(pages),
        model=model,
        fallback_pages=fallback_pages,
    )
