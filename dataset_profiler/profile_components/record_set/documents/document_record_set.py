import glob
from enum import Enum

import pandas as pd
import uuid
import numpy as np

from dataset_profiler.profile_components.record_set.documents.pdf.pdf_record_set import PdfRecordSet
from dataset_profiler.profile_components.record_set.documents.text.text_record_set import TextRecordSet
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    ColumnField,
)
from dataset_profiler.utilities import find_column_type_in_csv

class FileType(Enum):
    TEXT = "text"
    PDF = "pdf"


class DocumentRecordSet(RecordSet):
    def __init__(self, distribution_path: str, file_set: str, file_set_id: str, file_type: FileType):
        self.distribution_path = distribution_path
        self.file_set = file_set
        self.file_set_id = file_set_id
        self.type = "cr:RecordSet"
        self.file_type = file_type
        self.name = file_set
        self.description = ""
        self.fields = self.extract_fields()

    def extract_fields(self):
        documents = glob.glob(f"{self.distribution_path}{self.file_set}/*")

        document_list = []
        for doc_path in documents:
            match self.file_type:
                case FileType.TEXT:
                    document_content = TextRecordSet(self.distribution_path, doc_path, self.file_set_id)
                case FileType.PDF:
                    document_content = PdfRecordSet(self.distribution_path, doc_path, self.file_set_id)
                case _:
                    continue
            document_list.append(document_content)

        return document_list

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": self.name,
            "description": self.description,
            # "key": self.key,
            "field": [field.to_dict() for field in self.fields],
        }
