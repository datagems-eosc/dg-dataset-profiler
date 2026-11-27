"""CPU-only PDF text and Markdown: PyMuPDF4LLM with Tesseract OCR on pages without text.

Ported from the PyMuPDF4LLM baseline of the PDF-to-Markdown benchmark (about
1.4s per MathE document, 410/410 converted). Changes over the benchmark:

* The profiler takes plain text (pdf_to_text_light): Markdown's emphasis
  around every math variable ("matrix _A_ ,") only fragments CDD's chunks.
  The Markdown variant serves the endpoint's "fast" conversion.
* PyMuPDF4LLM's layout model classifies formula regions as images and leaves
  their text out, so a page of formulas comes back nearly empty. A page whose
  output holds clearly fewer words than its text layer falls back to the text
  layer.
* Every failure degrades to the plain text layer, then to "", so one bad PDF
  never fails a profiling job.
"""

import os
import re

import pymupdf

from dataset_profiler.configs.config_logging import logger

DEFAULT_OCR_LANGUAGE = "eng"

# A page whose layout output keeps fewer words than this share of its text
# layer lost content to the layout model (formulas) and uses the text layer instead.
MIN_LAYOUT_TO_TEXT_LAYER_RATIO = 0.7

# Below this many words a text layer is too small for the ratio to mean
# anything (page numbers, a stray header on a scanned page).
MIN_TEXT_LAYER_WORDS = 20


_PICTURE_TEXT_MARKER = re.compile(r"<!-- (Start|End) of picture text -->")


def clean_markdown(text: str) -> str:
    """Plain text from PyMuPDF4LLM's picture-text blocks, without U+FFFD.

    Text found inside images comes wrapped in HTML comments with <br> line
    breaks; PDFs whose fonts lack a Unicode mapping yield replacement
    characters. Neither helps CDD's chunks or the keyword prompt.
    """
    text = _PICTURE_TEXT_MARKER.sub("", text)
    text = text.replace("<br>", "\n").replace("�", "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def ocr_language() -> str:
    """Tesseract languages, e.g. "eng" or "eng+deu+fra" (DOCUMENT_OCR_LANGUAGE)."""
    return os.environ.get("DOCUMENT_OCR_LANGUAGE") or DEFAULT_OCR_LANGUAGE


def is_ocr_enabled() -> bool:
    return os.environ.get("DOCUMENT_OCR_ENABLED", "true").lower() in ["1", "true", "yes", "on"]


def _tesseract_available() -> bool:
    try:
        return bool(pymupdf.get_tessdata())
    except Exception:  # noqa: BLE001 - raises when no tessdata folder exists
        return False


def text_layer(pdf_path: str) -> str:
    """The PDF's embedded text, pages joined by blank lines, or "" on failure."""
    try:
        with pymupdf.open(pdf_path) as doc:
            return "\n\n".join(page.get_text() for page in doc)
    except Exception as e:  # noqa: BLE001 - logged, never raised
        logger.error("Failed to read PDF text layer", pdf_path=pdf_path, error=str(e))
        return ""


def _layout_pages(pdf_path: str, use_ocr: bool, language: str, markdown: bool) -> list[str]:
    import pymupdf4llm
    from pymupdf4llm.helpers import document_layout
    from pymupdf4llm.ocr import tesseract_api

    # PyMuPDF4LLM collects parser messages in a module-level buffer that it
    # never really empties, so every call would print all earlier documents'
    # messages again.
    document_layout.INFO_MESSAGES.seek(0)
    document_layout.INFO_MESSAGES.truncate(0)

    convert = pymupdf4llm.to_markdown if markdown else pymupdf4llm.to_text
    with pymupdf.open(pdf_path) as doc:
        chunks = convert(
            doc,
            page_chunks=True,
            use_ocr=use_ocr,
            ocr_function=tesseract_api.exec_ocr if use_ocr else None,
            ocr_language=language,
            show_progress=False,
        )
    return [chunk.get("text") or "" for chunk in chunks]


def pdf_to_text_light(pdf_path: str) -> str:
    """Plain text of the whole PDF in reading order, pages separated by blank lines.

    What the profiler uses for keywords, summaries and CDD's raw_content:
    plain text, like before, but with OCR for pages without a text layer.
    """
    return _extract(pdf_path, markdown=False)


def pdf_to_markdown_light(pdf_path: str) -> str:
    """Markdown of the whole PDF (headings, lists, tables), pages separated by blank lines."""
    return _extract(pdf_path, markdown=True)


def _extract(pdf_path: str, markdown: bool) -> str:
    """Pages without a text layer are OCRed with Tesseract when it is installed
    (DOCUMENT_OCR_ENABLED, on by default). Without Tesseract they are skipped,
    as before.
    """
    use_ocr = is_ocr_enabled() and _tesseract_available()
    try:
        with pymupdf.open(pdf_path) as doc:
            layer_pages = [page.get_text() for page in doc]
        layout_pages = _layout_pages(pdf_path, use_ocr, ocr_language(), markdown)
    except Exception as e:  # noqa: BLE001 - logged, falls back to the text layer
        logger.warning("Layout extraction failed, using the PDF text layer",
                       pdf_path=pdf_path, error=str(e))
        return clean_markdown(text_layer(pdf_path))

    if len(layout_pages) != len(layer_pages):
        logger.warning("Layout output and text layer disagree on the page count, using the text layer",
                       pdf_path=pdf_path, layout_pages=len(layout_pages),
                       layer_pages=len(layer_pages))
        return clean_markdown("\n\n".join(layer_pages))

    pages = []
    text_layer_pages = []
    for number, (layout_page, layer) in enumerate(zip(layout_pages, layer_pages), start=1):
        layer_words = len(layer.split())
        if (layer_words >= MIN_TEXT_LAYER_WORDS
                and len(layout_page.split()) < MIN_LAYOUT_TO_TEXT_LAYER_RATIO * layer_words):
            pages.append(layer)
            text_layer_pages.append(number)
        else:
            pages.append(layout_page)

    if text_layer_pages:
        logger.info("Used the text layer for pages the layout model emptied",
                    pdf_path=pdf_path, pages=text_layer_pages)
    if not use_ocr and any(len(layer.split()) < MIN_TEXT_LAYER_WORDS for layer in layer_pages):
        logger.info("Pages without a text layer were not OCRed (Tesseract unavailable or disabled)",
                    pdf_path=pdf_path)
    return "\n\n".join(cleaned for cleaned in map(clean_markdown, pages) if cleaned)
