"""CDD chunks PDFs itself, so the profiler passes it the whole text as one string.

Agreed with CDD (George Katsogiannis, Nov 2026): ``chunked_content`` was dropped
and PDF entries carry ``raw_content`` instead, next to ``content.file_path``.
"""

from dataset_profiler.profile_components.record_set.pdf.pdf_record_set import (
    PdfRecordSet,
    parse_pdf,
)

PDF = "tests/assets/dummy_data/data/pdfs/960.pdf"


def test_cdd_entry_carries_the_whole_text_unchunked():
    cdd = PdfRecordSet(file_object=PDF, distribution_id="pdf-1").to_dict_cdd()

    assert "chunked_content" not in cdd
    assert isinstance(cdd["raw_content"], str)
    assert cdd["raw_content"] == parse_pdf(PDF)
    # All three pages, not just the first chunk.
    assert "The spectrum of a matrix A" in cdd["raw_content"]
    assert "Elementary Linear Algebra" in cdd["raw_content"]
    assert cdd["content"] == {"type": "application/pdf", "file_path": PDF}


def test_unparseable_pdf_gives_empty_raw_content(monkeypatch):
    def broken_loader(path):
        raise RuntimeError("no text layer")

    monkeypatch.setattr(
        "dataset_profiler.profile_components.record_set.pdf.pdf_record_set.PyMuPDFLoader",
        broken_loader,
    )
    cdd = PdfRecordSet(file_object=PDF, distribution_id="pdf-1").to_dict_cdd()

    assert cdd["raw_content"] == ""
