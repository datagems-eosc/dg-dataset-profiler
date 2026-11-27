"""Vision-model transcription for the MathE document endpoints, model faked."""

import threading
from types import SimpleNamespace

import pymupdf
import pytest

from dataset_profiler.document_processing import vlm_transcription
from dataset_profiler.document_processing.light_extraction import clean_markdown
from dataset_profiler.document_processing.service import (
    ConversionMode,
    convert_document,
)
from dataset_profiler.document_processing.vlm_transcription import (
    TranscriptionError,
    UnsupportedDocumentError,
    strip_outer_fence,
    transcribe_document,
)

THREE_PAGE_PDF = "tests/assets/dummy_data/data/pdfs/960.pdf"


def _response(content, finish_reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content), finish_reason=finish_reason)])


class FakeConnector:
    """Answers each page with its call number; fails the calls listed in ``fail``."""

    def __init__(self, fail=()):
        self.fail = set(fail)
        self.calls = 0
        self.lock = threading.Lock()
        self.kwargs = []

    def chat(self, message, stream=False, **kwargs):
        with self.lock:
            self.calls += 1
            call = self.calls
            self.kwargs.append(kwargs)
        if call in self.fail:
            return _response("", finish_reason="length")
        image = message[0]["content"][1]["image_url"]["url"]
        assert image.startswith("data:image/png;base64,")
        return _response(f"```markdown\n# Page transcription {call}\n```")


@pytest.fixture
def fake_vlm(monkeypatch):
    connector = FakeConnector()
    monkeypatch.setattr(vlm_transcription, "_build_connector", lambda model: connector)
    for name in ("DOCUMENT_VLM_MODEL", "DOCUMENT_VLM_MAX_TOKENS", "DOCUMENT_VLM_MAX_ATTEMPTS",
                 "DOCUMENT_MAX_PAGES"):
        monkeypatch.delenv(name, raising=False)
    # One page at a time, so call numbers follow page order.
    monkeypatch.setenv("DOCUMENT_VLM_MAX_CONCURRENCY", "1")
    return connector


def test_every_page_is_transcribed_in_order(fake_vlm):
    result = transcribe_document(THREE_PAGE_PDF)
    assert result.pages == 3
    assert result.model == "glm-5.3-flash"
    assert result.fallback_pages == []
    assert result.markdown.split("\n\n") == [
        "# Page transcription 1", "# Page transcription 2", "# Page transcription 3"]
    assert fake_vlm.kwargs[0]["temperature"] == 0
    assert fake_vlm.kwargs[0]["max_tokens"] == 8000


def test_model_comes_from_the_environment(fake_vlm, monkeypatch):
    monkeypatch.setenv("DOCUMENT_VLM_MODEL", "qwen3.6")
    assert transcribe_document(THREE_PAGE_PDF).model == "qwen3.6"


def test_failed_page_is_retried_then_keeps_its_text_layer(fake_vlm, monkeypatch):
    monkeypatch.setenv("DOCUMENT_VLM_MAX_ATTEMPTS", "2")
    # Page 2 is the 2nd call; its retry is the 3rd. Both fail.
    fake_vlm.fail = {2, 3}
    result = transcribe_document(THREE_PAGE_PDF)
    assert result.fallback_pages == [2]
    with pymupdf.open(THREE_PAGE_PDF) as doc:
        page_two = clean_markdown(doc[1].get_text())
    assert result.markdown == "\n\n".join(
        ["# Page transcription 1", page_two, "# Page transcription 4"])


def test_all_pages_failing_is_an_error(fake_vlm, monkeypatch):
    monkeypatch.setenv("DOCUMENT_VLM_MAX_ATTEMPTS", "1")
    fake_vlm.fail = {1, 2, 3}
    with pytest.raises(TranscriptionError, match="any page"):
        transcribe_document(THREE_PAGE_PDF)


def test_text_files_are_returned_as_they_are(tmp_path, fake_vlm):
    path = tmp_path / "notes.txt"
    path.write_text("Limits of functions\n")
    assert transcribe_document(str(path)).markdown == "Limits of functions"
    assert fake_vlm.calls == 0


def test_unsupported_type_is_rejected(tmp_path):
    path = tmp_path / "slides.pptx"
    path.write_bytes(b"x")
    with pytest.raises(UnsupportedDocumentError):
        transcribe_document(str(path))


def test_strip_outer_fence():
    assert strip_outer_fence("```markdown\n# A\n\n$x$\n```") == "# A\n\n$x$"
    assert strip_outer_fence("# A\n```python\nx = 1\n```") == "# A\n```python\nx = 1\n```"


def test_fast_mode_uses_the_cpu_extraction(fake_vlm):
    result = convert_document(THREE_PAGE_PDF, ConversionMode.FAST)
    assert "The spectrum of a matrix" in result.markdown
    assert result.model == ""
    assert fake_vlm.calls == 0


def test_fast_mode_refuses_images(tmp_path):
    path = tmp_path / "page.png"
    path.write_bytes(b"\x89PNG")
    with pytest.raises(UnsupportedDocumentError, match="quality"):
        convert_document(str(path), ConversionMode.FAST)


def test_page_limit(monkeypatch):
    monkeypatch.setenv("DOCUMENT_MAX_PAGES", "2")
    with pytest.raises(UnsupportedDocumentError, match="3 pages"):
        convert_document(THREE_PAGE_PDF, ConversionMode.FAST)
