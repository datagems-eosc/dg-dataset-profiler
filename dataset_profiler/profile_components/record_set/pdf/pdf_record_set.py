from typing import Dict, List, Any
from dataset_profiler.profile_components.record_set.record_set_abc import RecordSet

from dataset_profiler.profile_components.record_set.pdf.pdf_utilities import (
    get_pdf_profile,
    get_pdf_document,
)
from dataset_profiler.profile_components.record_set.text.text_utilities import (
    get_keywords,
    get_summary,
)

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", None)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", None)


class PdfRecordSet(RecordSet):
    def __init__(
        self,
        distribution_path: str,
        file_object: str,
    ):
        self.distribution_path = distribution_path
        self.file_object = file_object
        self.type = "cr:RecordSet"
        self.name = file_object.split(".")[-2]
        # self.description = ""

        self.key = {"@id": self.name}

        profile = get_pdf_profile(distribution_path + file_object)
        self.file_size_bytes = profile["file_size_bytes"]
        self.subject = profile["subject"]
        self.author = profile["author"]
        self.title = profile["title"]
        self.producer = profile["producer"]
        self.creator = profile["creator"]
        self.creation_date = profile["creation_date"]
        self.modification_date = profile["modification_date"]
        self.pages_count = profile["pages_count"]

        # extract document of pdf
        document = get_pdf_document(distribution_path + file_object)
        print("Document extracted successfully.")
        print(document)
        self.keywords = get_keywords(
            document,
            model=OLLAMA_MODEL,
            base_url=OLLAMA_API_BASE_URL,
            max_keywords_num=5,
        ).keywords
        self.summary = get_summary(
            document, model=OLLAMA_MODEL, base_url=OLLAMA_API_BASE_URL, max_words=800
        )
        print("***KEY WORDS***", self.keywords)
        print("***SUMMARY***", self.summary)

    def extract_fields(self) -> List:
        return []  # PDF records do not have fields like text records

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the PdfRecordSet to a dictionary representation.
        :return: Dictionary representation of the PdfRecordSet.
        """
        return {
            "distribution_path": self.distribution_path,
            "file_object": self.file_object,
            "name": self.name,
            "file_size_bytes": self.file_size_bytes,
            "subject": self.subject,
            "author": self.author,
            "title": self.title,
            "producer": self.producer,
            "creator": self.creator,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "pages_count": self.pages_count,
            "keywords": self.keywords,
            "summary": self.summary,
        }
