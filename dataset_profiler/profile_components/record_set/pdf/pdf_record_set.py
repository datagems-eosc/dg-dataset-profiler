import uuid
import os
from pathlib import Path
from typing import Dict, List, Any
from dataset_profiler.profile_components.record_set.record_set_abc import RecordSet
from langchain_community.document_loaders import PyMuPDFLoader

from dataset_profiler.profile_components.record_set.pdf.pdf_utilities import (
    get_pdf_profile,
)
from dataset_profiler.profile_components.record_set.document_description import (
    describe_document,
)
from dataset_profiler.profile_components.distribution import get_original_format
from dataset_profiler.configs.config_logging import logger


def parse_pdf(pdf_path) -> str:
    """Return the PDF's full text from its text layer, or "" on failure.

    Feeds the keywords and summary, and is passed whole to CDD as
    ``raw_content`` for it to chunk. No OCR is run, so a scanned PDF gives "".
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} was not found.")

    try:
        documents = PyMuPDFLoader(pdf_path).load()
        return "\n\n".join(page.page_content for page in documents)

    except Exception as e:
        logger.error("Failed to parse PDF", pdf_path=pdf_path, error=str(e))
        return ""


class PdfRecordSet(RecordSet):
    def __init__(
        self,
        file_object: str,
        distribution_id: str
    ):
        super().__init__()
        self.file_object = file_object
        self.file_object_id = distribution_id
        self.type = "cr:RecordSet"
        self.name = file_object.split("/")[-1]
        # self.description = ""

        self.key = {"@id": self.name}

        profile = get_pdf_profile(file_object)
        self.file_size_bytes = profile["file_size_bytes"]
        self.subject = profile["subject"]
        self.author = profile["author"]
        self.title = profile["title"]
        self.producer = profile["producer"]
        self.creator = profile["creator"]
        self.creation_date = profile["creation_date"]
        self.modification_date = profile["modification_date"]
        self.pages_count = profile["pages_count"]
        self.text = parse_pdf(file_object)
        description = describe_document(self.text, name=self.name)
        self.keywords = description.keywords
        self.summary = description.summary

    def extract_fields(self) -> List:
        return []  # PDF records do not have fields like text records

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the PdfRecordSet to a dictionary representation.
        :return: Dictionary representation of the PdfRecordSet.
        """
        return {
            # "file_object": self.file_object,
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": self.name,
            "source": {
                "@type": "cr:FileObject",
                "@id": self.file_object_id,
            },
            # "file_size_bytes": self.file_size_bytes,
            "subject": self.subject,
            "author": self.author,
            "title": self.title,
            "producer": self.producer,
            "creator": self.creator,
            "creationDate": self.creation_date,
            "modificationDate": self.modification_date,
            "pagesCount": self.pages_count,
            "keywords": self.keywords,
            "summary": self.summary,
            "field": []  # TODO ADD CHUNKING
        }

    def to_dict_cdd(self):
        return {
            "file_object_id": self.file_object_id,
            "original_format": get_original_format(self.file_object),
            "source_file": self.file_object,
            "name": Path(self.name).name,
            "description": self.summary,
            "keywords": self.keywords,
            "content": {
                "type": "application/pdf",
                "file_path": self.file_object,
            },
            # Unchunked: CDD chunks it, as it does every other document.
            "raw_content": self.text,
        }
