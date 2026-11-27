"""Convert a document to Markdown: the work behind the MathE document endpoints.

Two modes:

* ``quality`` (default): every page goes to the SCAYLE vision model
  (vlm_transcription). Handles scans, handwriting and formulas; several
  seconds per page.
* ``fast``: the profiler's CPU extraction (light_extraction). About a second
  per document, but no handwriting and formulas come out as plain text.
"""

import os
from enum import Enum
from pathlib import Path

import pymupdf
from pydantic import BaseModel, Field

from dataset_profiler.document_processing.light_extraction import pdf_to_markdown_light
from dataset_profiler.document_processing.vlm_transcription import (
    IMAGE_MIME_TYPES,
    SUPPORTED_SUFFIXES,
    TEXT_SUFFIXES,
    UnsupportedDocumentError,
    transcribe_document,
)

DEFAULT_MAX_PAGES = 300


class ConversionMode(str, Enum):
    QUALITY = "quality"
    FAST = "fast"


class ConvertResult(BaseModel):
    """Markdown of a document.

    ## Attributes
    * **markdown**: the document as Markdown, with LaTeX math in quality mode
    * **pages**: number of pages (1 for an image or a text file)
    * **mode**: the conversion mode used
    * **model**: the vision model, or "" when none was used
    * **fallback_pages**: pages the vision model failed on; they hold the PDF's text layer
    """
    markdown: str
    pages: int
    mode: ConversionMode
    model: str = ""
    fallback_pages: list[int] = Field(default_factory=list)


def max_pages() -> int:
    value = os.environ.get("DOCUMENT_MAX_PAGES")
    return int(value) if value else DEFAULT_MAX_PAGES


def _check_document(path: str) -> int:
    """Raise UnsupportedDocumentError for an unknown type or too many pages; return the pages."""
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedDocumentError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )
    if suffix != ".pdf":
        return 1
    try:
        with pymupdf.open(path) as doc:
            pages = doc.page_count
    except Exception as e:  # noqa: BLE001 - reported to the caller as an unreadable file
        raise UnsupportedDocumentError(f"The PDF cannot be read: {e}") from e
    if pages > max_pages():
        raise UnsupportedDocumentError(
            f"The PDF has {pages} pages; at most {max_pages()} are accepted"
        )
    return pages


def convert_document(path: str, mode: ConversionMode = ConversionMode.QUALITY) -> ConvertResult:
    pages = _check_document(path)
    suffix = Path(path).suffix.lower()

    if mode == ConversionMode.QUALITY:
        transcription = transcribe_document(path)
        return ConvertResult(
            markdown=transcription.markdown,
            pages=transcription.pages,
            mode=mode,
            model=transcription.model,
            fallback_pages=transcription.fallback_pages,
        )

    if suffix in IMAGE_MIME_TYPES:
        raise UnsupportedDocumentError("Images need the 'quality' mode")
    if suffix in TEXT_SUFFIXES:
        markdown = Path(path).read_text(encoding="utf-8", errors="replace").strip()
    else:
        markdown = pdf_to_markdown_light(path)
    return ConvertResult(markdown=markdown, pages=pages, mode=mode)
