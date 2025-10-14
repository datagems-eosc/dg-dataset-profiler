
from collections.abc import Iterable
from typing import Dict, Union
from pathlib import Path
from pikepdf import Pdf
from docling_core.types.doc.labels import DocItemLabel
from docling_core.types.doc.document import DoclingDocument, TextItem, NodeItem
from docling.datamodel.base_models import InputFormat, ItemAndImageEnrichmentElement
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.models.base_model import BaseItemAndImageEnrichmentModel
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from io import BytesIO
from ollama import Client
import base64
import logging
import os


class LLMFormulaUnderstandingPipelineOptions(PdfPipelineOptions):
    do_formula_understanding: bool = False
    model: str = "granite3.2-vision"


# A new enrichment model using both the document element and its image as input
class LLMFormulaUnderstandingEnrichmentModel(BaseItemAndImageEnrichmentModel):
    images_scale = 1.0

    def __init__(self, enabled: bool, model: str):
        self.enabled = enabled
        self.model = model

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return (
            self.enabled
            and isinstance(element, TextItem)
            and element.label == DocItemLabel.FORMULA
        )

    def process_image_with_ollama(self, image):
        # Convert the image to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        logging.info(
            "Starting Ollama generate for formula image (size: %d bytes)", len(img_str)
        )
        # Call the ollama API
        try:
            client = Client(timeout=30)
            response = client.generate(
                model=self.model,
                prompt="Extract the formula from this image in a markdown math format. All greek letters should be escaped with a backslash.",
                images=[img_str],  # Pass the base64 encoded image
            )
            logging.info("Ollama response received successfully.")
            return response["response"].strip()
        except Exception as e:
            logging.error(f"Error processing formula with ollama: {e}")
            return None

    def __call__(
        self,
        doc: DoclingDocument,
        element_batch: Iterable[ItemAndImageEnrichmentElement],
    ) -> Iterable[NodeItem]:
        if not self.enabled:
            return

        for enrich_element in element_batch:
            # enrich_element.image.show()
            image = enrich_element.image
            # Process the image with ollama to extract the formula
            processed_formula = self.process_image_with_ollama(image)
            logging.info(
                f"Processed formula: {processed_formula} for element: {enrich_element.item}"
            )
            if isinstance(enrich_element.item, TextItem):
                if processed_formula is not None:
                    enrich_element.item.text = processed_formula
                else:
                    logging.warning(
                        f"Failed to process formula for element: {enrich_element.item}"
                    )
            yield enrich_element.item
            logging.info("Yielded processed element: %s", enrich_element.item)


# How the pipeline can be extended.
class LLMFormulaUnderstandingPipeline(StandardPdfPipeline):
    def __init__(self, pipeline_options: LLMFormulaUnderstandingPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options = pipeline_options

        self.enrichment_pipe = [
            LLMFormulaUnderstandingEnrichmentModel(
                enabled=self.pipeline_options.do_formula_understanding,
                model=self.pipeline_options.model,
            )
        ]

        if self.pipeline_options.do_formula_understanding:
            self.keep_backend = True

    @classmethod
    def get_default_options(cls) -> LLMFormulaUnderstandingPipelineOptions:
        # Provide a default model name, we use Granite here
        return LLMFormulaUnderstandingPipelineOptions(model="granite3.2-vision")


def get_pdf_document(input_doc_path: Path | str) -> str:
    """
    Converts a PDF document to a DoclingDocument using the LLMFormulaUnderstandingPipeline.
    :param input_doc_path: Path to the input PDF document.
    :return: DoclingDocument object.
    """
    if isinstance(input_doc_path, str):
        input_doc_path = Path(input_doc_path)
    if not input_doc_path.exists():
        raise FileNotFoundError(f"Input document not found: {input_doc_path}")
    if not input_doc_path.is_file():
        raise ValueError(f"Input path is not a file: {input_doc_path}")
    if not input_doc_path.suffix.lower() == ".pdf":
        raise ValueError(f"Input path is not a PDF file: {input_doc_path}")
    # Set up logging
    if not logging.getLogger().hasHandlers():
        # Configure logging to output to console
        logging.basicConfig(level=logging.INFO)

    pipeline_options = LLMFormulaUnderstandingPipelineOptions()
    pipeline_options.do_formula_understanding = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=LLMFormulaUnderstandingPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )
    doc = doc_converter.convert(input_doc_path).document
    md_doc = doc.export_to_markdown()
    if not isinstance(doc, DoclingDocument):
        raise ValueError("Converted document is not a DoclingDocument.")
    return md_doc


def get_pdf_profile(input_doc_path: Path | str) -> Dict[str, Union[str, int, float]]:
    """
    Extracts metadata from a PDF document.
    :param input_doc_path: Path to the input PDF document.
    :return: Dictionary containing metadata of the PDF document.
    """
    # load the PDF document
    file_size = os.path.getsize(input_doc_path)
    pdf = Pdf.open(input_doc_path)
    meta_dict = dict(pdf.docinfo)
    profile = {
        "file_size_bytes": file_size,
        "subject": str(meta_dict.get("/Subject", "")),
        "author": str(meta_dict.get("/Author", "")),
        "title": str(meta_dict.get("/Title", "")),
        "producer": str(meta_dict.get("/Producer", "")),
        "creator": str(meta_dict.get("/Creator", "")),
        "creation_date": str(meta_dict.get("/CreationDate", "")),
        "modification_date": str(meta_dict.get("/ModDate", "")),
        "pages_count": len(pdf.pages),
    }
    return profile
