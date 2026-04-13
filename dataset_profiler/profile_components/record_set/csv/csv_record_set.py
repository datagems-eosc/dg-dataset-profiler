import csv
import json
import tempfile
import os
from pathlib import Path

import pandas as pd
import uuid
import numpy as np

from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.csv.calculate_statistics import (
    calculate_column_statistics,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    ColumnField,
)
from dataset_profiler.utilities import find_column_type_in_csv
from dataset_profiler.configs.config_logging import logger


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
        self.examples = self.extract_examples()

    def _read_csv_with_delimiter_detection(self, file_path):
        """Common method to read CSV files with delimiter detection and flexible parsing."""
        if not os.path.exists(file_path):
            logger.error("CSV file not found", file=file_path)
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        logger.info("Reading CSV file with delimiter detection", file=file_path)

        # Try to detect the delimiter using the csv module
        try:
            with open(file_path, 'r', encoding="ISO-8859-1") as csvfile:
                sample = csvfile.read(1024)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
                    logger.info(f"Detected delimiter: '{delimiter}'", file=file_path)
                except:
                    # If sniffer fails, try common delimiters
                    delimiter = ','
                    logger.info(f"Using default delimiter: '{delimiter}'", file=file_path)

            # Use the detected delimiter with flexible parsing
            csv_object = pd.read_csv(
                file_path,
                encoding="ISO-8859-1",
                sep=delimiter,
                on_bad_lines='skip'  # For pandas >= 1.3.0
                # error_bad_lines=False  # For older pandas versions
            )

            return csv_object

        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}", file=file_path)
            # Try with Python engine as a fallback
            try:
                logger.info("Trying with Python engine as fallback", file=file_path)
                csv_object = pd.read_csv(
                    file_path,
                    encoding="ISO-8859-1",
                    engine='python'
                )
                return csv_object
            except pd.errors.EmptyDataError:
                logger.warning(f"Empty CSV given. Skipping...", file=file_path)
            except Exception as e2:
                logger.error(f"Fallback also failed: {str(e2)}", file=file_path)
                raise e

    def extract_fields(self):
        file_path = os.path.join(self.distribution_path, self.file_object)
        logger.info("Extracting fields from CSV file", file=file_path)

        csv_object = self._read_csv_with_delimiter_detection(file_path)

        fields = []
        for column in csv_object.columns:
            fields.append(
                TableColumnField(
                    csv_object[column], column, self.name, self.file_object_id
                )
            )
        return fields

    def extract_examples(self):
        file_path = os.path.join(self.distribution_path, self.file_object)
        logger.info("Extracting examples from CSV file", file=file_path)

        csv_object = self._read_csv_with_delimiter_detection(file_path)
        # Convert NaN values to None in the examples dictionary
        examples_dict = csv_object.head(30).to_dict(orient="list")
        for key in examples_dict:
            examples_dict[key] = [None if pd.isna(x) else x for x in examples_dict[key]]
        return examples_dict


    def to_dict(self):
        return {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": Path(self.name).name,
            # "description": self.description,
            # "key": self.key,
            "field": [field.to_dict() for field in self.fields],
            "examples": json.dumps(self.examples, default=str),
        }

    def to_dict_cdd(self):
        return {
            "file_object_id": self.file_object_id,
            "original_format": "csv",
            "source_file": os.path.join(self.distribution_path, self.file_object),
            "name": Path(self.name).name,
            "description": "",
            "keywords": [],
            "columns": [field.to_dict_cdd() for field in self.fields],
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
        if len(column) > 10:
            # Fix the replace method to handle NaN values properly
            sample_data = column.sample(10)
            # Convert NaN values to None in Python
            self.sample = [None if pd.isna(x) else x for x in sample_data.tolist()]
        else:
            # Convert NaN values to None in Python
            self.sample = [None if pd.isna(x) else x for x in column.tolist()]
        self.statistics: ColumnStatistics = calculate_column_statistics(column)

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "dataType": self.dataType,
            "source": self.source,
            "sample": self.sample,
            "statistics": self.statistics.to_dict(),
        }

    def to_dict_cdd(self):
        return {
            "name": self.name,
            "primitive_type": self.dataType,
            "semantic_types": [],
            "description": self.description,
            "statistics": self.statistics.to_dict_cdd(),
        }


def get_record_sets_from_excel(
    distribution_path: str, file_object: str, file_object_id: str
) -> list[CSVRecordSet]:
    with tempfile.TemporaryDirectory() as temp_dir:
        xls = pd.ExcelFile(os.path.join(distribution_path, file_object))
        record_sets = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            if df.empty:
                logger.warning(
                    f"Found empty sheet {sheet_name} in {file_object}. Skipping this sheet."
                )
                continue
            df.to_csv(os.path.join(temp_dir, f"{sheet_name}.csv"), index=False, sep=",")
            try:
                record_set = CSVRecordSet(
                    distribution_path=temp_dir,
                    file_object=f"{sheet_name}.csv",
                    file_object_id=file_object_id,
                )
            except (pd.errors.ParserError, csv.Error) as e:
                # print the stack trace for debugging purposes
                logger.warning(
                    f"Failed to process sheet {sheet_name} in {file_object} with error {e}. Skipping this sheet."
                )
                continue
            record_sets.append(record_set)

    # Store the current sheet name for each record set
    for i, (record_set, sheet_name) in enumerate(zip(record_sets, xls.sheet_names)):
        record_set.inject_distribution = {
            "@type": "cr:FileObject",
            "@id": str(uuid.uuid4()),
            "name": sheet_name,
            "description": "",
            "containedIn": {"@id": file_object_id},
            "encodingFormat": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

    return record_sets
