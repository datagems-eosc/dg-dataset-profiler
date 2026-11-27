"""Document text extraction and transcription.

Two flows share this package:

* the profiling pipeline, which must stay light: ``light_extraction`` turns a
  PDF into text on the CPU, with Tesseract OCR for pages without a text layer;
* the MathE document endpoints (``routes/documents.py``), which may use heavier
  models: ``vlm_transcription`` sends every page to a SCAYLE vision model.
  ``file_objects`` finds a FileObject's PDF through MoMa, ``ap_payload`` reads
  and fills the Analytical Pattern, and ``markdown_cache`` keeps conversions.
"""
