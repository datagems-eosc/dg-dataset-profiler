import pandas as pd
import uuid
import numpy as np
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    ColumnField,
)
from dataset_profiler.utilities import find_column_type_in_csv


class CSVRecordSet(RecordSet):
    def __init__(self, distribution_path: str, file_object: str, file_object_id: str):
        self.distribution_path = distribution_path
        self.file_object = file_object
        self.file_object_id = file_object_id
        self.type = "cr:RecordSet"
        self.name = file_object.split(".")[-2]
        self.description = ""
        self.fields = self.extract_fields()

    def extract_fields(self):
        csv_object = pd.read_csv(self.distribution_path + self.file_object, sep=None, encoding = "ISO-8859-1")

        fields = []
        for column in csv_object.columns:
            fields.append(
                CSVColumnField(
                    csv_object[column], column, self.name, self.file_object_id
                )
            )

        return fields

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": self.name,
            "description": self.description,
            # "key": self.key,
            "field": [field.to_dict() for field in self.fields],
        }


class CSVColumnField(ColumnField):
    def __init__(
        self, column: pd.Series, column_name: str, csv_name: str, file_object_id: str
    ):
        self.type = "cr:Field"
        self.id = str(uuid.uuid4())
        self.name = column_name
        self.description = ""
        self.dataType = find_column_type_in_csv(column)
        self.source = {
            "fileObject": {"@id": file_object_id},
            "extract": {"column": column_name},
        }
        self.sample = column.sample(3).replace({np.nan: None}).tolist()

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "dataType": self.dataType,
            "source": self.source,
            "sample": self.sample,
        }
