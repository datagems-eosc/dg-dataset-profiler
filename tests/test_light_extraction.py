"""CPU PDF extraction used by the profiler: PyMuPDF4LLM, Tesseract, text-layer fallback."""

from types import SimpleNamespace

import pymupdf
import pytest

from dataset_profiler.document_processing import light_extraction
from dataset_profiler.document_processing.light_extraction import (
    clean_markdown,
    pdf_to_markdown_light,
    pdf_to_text_light,
)

MATHE_PDFS = "tests/assets/mathe_integration_techniques/data/PDF"
# A page of integration formulas: PyMuPDF4LLM's layout model files them as
# images and drops their text.
FORMULA_PDF = f"{MATHE_PDFS}/134.pdf"
# Scanned pages: 10 words in the text layer.
SCANNED_PDF = f"{MATHE_PDFS}/136.pdf"
TEXT_PDF = "tests/assets/dummy_data/data/pdfs/960.pdf"

needs_tesseract = pytest.mark.skipif(
    not light_extraction._tesseract_available(), reason="Tesseract language data not installed"
)


def _words(text: str) -> int:
    return len(text.split())


def _text_layer_words(path: str) -> int:
    with pymupdf.open(path) as doc:
        return sum(_words(page.get_text()) for page in doc)


def test_text_pdf_keeps_its_content():
    markdown = pdf_to_markdown_light(TEXT_PDF)
    assert "The spectrum of a matrix" in markdown
    assert _words(markdown) >= _text_layer_words(TEXT_PDF)


def test_profiler_text_has_no_markdown_markup():
    text = pdf_to_text_light(TEXT_PDF)
    assert "The spectrum of a matrix A" in text
    assert "_A_" not in text and "**" not in text


def test_formula_page_falls_back_to_the_text_layer():
    markdown = pdf_to_markdown_light(FORMULA_PDF)
    assert _words(markdown) >= 0.9 * _text_layer_words(FORMULA_PDF)
    assert "Trigonometric" in markdown


@needs_tesseract
def test_scanned_pages_are_ocred(monkeypatch):
    monkeypatch.setenv("DOCUMENT_OCR_ENABLED", "true")
    assert _words(pdf_to_markdown_light(SCANNED_PDF)) > 3 * _text_layer_words(SCANNED_PDF)


def test_ocr_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("DOCUMENT_OCR_ENABLED", "false")
    assert _words(pdf_to_markdown_light(SCANNED_PDF)) <= _text_layer_words(SCANNED_PDF) + 5


def test_layout_failure_falls_back_to_the_text_layer(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("layout model crashed")

    monkeypatch.setattr(light_extraction, "_layout_pages", broken)
    assert "The spectrum of a matrix" in pdf_to_markdown_light(TEXT_PDF)


def test_unreadable_pdf_gives_empty_text(monkeypatch):
    def broken_open(path):
        raise RuntimeError("cannot open document")

    monkeypatch.setattr(light_extraction, "pymupdf",
                        SimpleNamespace(open=broken_open, get_tessdata=lambda: None))
    assert pdf_to_markdown_light(TEXT_PDF) == ""


def test_clean_markdown_unwraps_picture_text_and_drops_replacement_characters():
    raw = ("Title�\n\n<!-- Start of picture text -->\nfirst line<br>second line<br>"
           "<!-- End of picture text -->\n\n\n\nEnd")
    assert clean_markdown(raw) == "Title\n\nfirst line\nsecond line\n\nEnd"
