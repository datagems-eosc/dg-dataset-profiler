import uuid
from typing import Dict, List, Any
from dataset_profiler.profile_components.record_set.record_set_abc import RecordSet

from dataset_profiler.profile_components.record_set.documents.pdf.pdf_utilities import (
    get_pdf_profile,
    get_pdf_document,
)
from dataset_profiler.profile_components.record_set.documents.text.text_utilities import (
    get_keywords_ollama,
    get_summary_ollama,
)

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", None)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", None)


class PdfRecordSet:
    def __init__(
        self,
        distribution_path: str,
        file_object: str,
        file_set_id
    ):
        self.distribution_path = distribution_path
        self.file_object = file_object
        self.type = "dg:Document"
        self.name = file_object.split("/")[-1].split(".")[-2]
        # self.description = ""

        # self.key = {"@id": self.name}
        self.id = str(uuid.uuid4())

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
        self.source = {
            "fileSet": {"@id": file_set_id},
        }

        # extract document of pdf
        # document = get_pdf_document(file_object)
        # self.keywords = get_keywords_ollama(
        #     document,
        #     model=OLLAMA_MODEL,
        #     base_url=OLLAMA_API_BASE_URL,
        #     max_keywords_num=5,
        # ).keywords
        # self.summary = get_summary_ollama(
        #     document, model=OLLAMA_MODEL, base_url=OLLAMA_API_BASE_URL, max_words=800
        # )
        self.keywords = ["Keyword 1", "Keyword 2"]
        self.summary = "This is an example summary"


    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the PdfRecordSet to a dictionary representation.
        :return: Dictionary representation of the PdfRecordSet.
        """
        return {
            "@type": self.type,
            "@id": self.id,
            # "distribution_path": self.distribution_path,
            # "file_object": self.file_object,
            "name": self.name,
            "file_size_bytes": self.file_size_bytes,
            # "subject": self.subject,
            # "author": self.author,
            # "title": self.title,
            # "producer": self.producer,
            # "creator": self.creator,
            # "creation_date": self.creation_date,
            # "modification_date": self.modification_date,
            # "pages_count": self.pages_count,
            "keywords": self.keywords,
            "summary": self.summary,
            "source": self.source
        }
