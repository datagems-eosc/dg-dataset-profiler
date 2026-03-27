import uuid
import os
from pathlib import Path
from typing import Dict, List, Any
from dataset_profiler.profile_components.record_set.record_set_abc import RecordSet
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from dataset_profiler.profile_components.record_set.pdf.pdf_utilities import (
    get_pdf_profile,
    get_pdf_document,
)
from dataset_profiler.profile_components.record_set.text.text_utilities import (
    get_keywords,
    get_summary,
)
from dataset_profiler.configs.config_logging import logger


# Default model for text processing using Scayle-LLM
SCAYLE_MODEL = "llama-3.3"


def parse_and_chunk_pdf(pdf_path, chunk_size=1000, chunk_overlap=200):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} was not found.")

    try:
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()

        # 2. CHUNK: Initialize the text splitter
        print("Chunking documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,       # Measured in characters, not words
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        # Split the parsed documents into smaller chunks
        chunks = text_splitter.split_documents(documents)
        string_chunks = [chunk.page_content for chunk in chunks]

        return string_chunks

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


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
        self.chunks = parse_and_chunk_pdf(file_object)
        # extract document of pdf
        # document = get_pdf_document(file_object)
        # logger.info("Document extracted successfully.", file_object=file_object)
        # self.keywords = get_keywords(
        #     document,
        #     model=SCAYLE_MODEL,
        #     max_keywords_num=5,
        # ).keywords
        # self.summary = get_summary(document, model=SCAYLE_MODEL, max_words=800)
        # logger.info("***KEY WORDS***", keywords=self.keywords)
        # logger.info("***SUMMARY***", summary=self.summary)
        self.keywords = []
        self.summary = ""

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
            "original_format": "application/pdf",
            "source_file": self.file_object,
            "name": Path(self.name).name,
            "description": self.summary,
            "keywords": self.keywords,
            "chunked_content": [
                {
                    "section": "",
                    "subsection": "",
                    "chunks": self.chunks
                }
            ],
            "content": {
                "type": "application/pdf",
                "file_path": self.file_object,
            },
        }
