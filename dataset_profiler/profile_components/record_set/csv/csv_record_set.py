import csv
import tempfile

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
        super().__init__()
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
                TableColumnField(
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


class TableColumnField(ColumnField):
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


def get_record_sets_from_excel(distribution_path: str, file_object: str, file_object_id: str) -> list[CSVRecordSet]:
    with tempfile.TemporaryDirectory() as temp_dir:
        xls = pd.ExcelFile(distribution_path + file_object)
        record_sets = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df.to_csv(temp_dir + '/' + f"{sheet_name}.csv", index=False, sep=',')
            try:
                record_set = CSVRecordSet(
                    distribution_path=temp_dir + '/',
                    file_object=f"{sheet_name}.csv",
                    file_object_id=file_object_id,
                )
            except (pd.errors.ParserError, csv.Error) as e:
                print(f"Failed to process sheet {sheet_name} in {file_object}. Skipping this sheet.")
                continue
            record_sets.append(record_set)

    for record_set in record_sets:
        record_set.inject_distribution = {
          "@type": "cr:FileObject",
          "@id": str(uuid.uuid4()),
          "name": sheet_name,
          "description": "",
          "containedIn": {
            "@id": file_object_id
          },
          "encodingFormat": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

    return record_sets
