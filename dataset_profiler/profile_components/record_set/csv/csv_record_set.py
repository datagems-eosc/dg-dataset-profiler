import csv
import json
import tempfile
import os
from pathlib import Path

import pandas as pd
import uuid

from dataset_profiler.data_quality import (
    detect_data_quality_errors,
    is_data_quality_enabled,
)
from dataset_profiler.data_quality.models import DataQualityResult
from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.csv.calculate_statistics import (
    _ColumnAccumulator,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    ColumnField,
)
from dataset_profiler.configs.config_logging import logger

# Rows read per chunk while streaming a CSV. Bounds peak memory regardless of
# how large the file is.
CHUNK_SIZE = 500_000


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
        self.data_quality = self.extract_data_quality()

    def _detect_delimiter(self, file_path):
        """Detect the CSV delimiter by sniffing the first 1KB of the file."""
        if not os.path.exists(file_path):
            logger.error("CSV file not found", file=file_path)
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        with open(file_path, 'r', encoding="ISO-8859-1") as csvfile:
            sample = csvfile.read(1024)
            try:
                delimiter = csv.Sniffer().sniff(sample).delimiter
                logger.info(f"Detected delimiter: '{delimiter}'", file=file_path)
            except csv.Error:
                # If sniffer fails, fall back to a comma
                delimiter = ','
                logger.info(f"Using default delimiter: '{delimiter}'", file=file_path)
        return delimiter

    def _read_column_names(self, file_path, delimiter):
        """Read only the header row to get the column names (no data loaded)."""
        try:
            header = pd.read_csv(
                file_path, encoding="ISO-8859-1", sep=delimiter, nrows=0
            )
        except pd.errors.EmptyDataError:
            logger.warning("Empty CSV given. Skipping...", file=file_path)
            return []
        return list(header.columns)

    def _iter_chunks(self, file_path, delimiter, usecols=None):
        """Yield the CSV in row chunks, falling back to the Python engine.

        Streaming in chunks keeps peak memory bounded to ``CHUNK_SIZE`` rows
        instead of the whole file, while still reading every row exactly once
        per pass.
        """
        read_kwargs = dict(
            encoding="ISO-8859-1",
            sep=delimiter,
            chunksize=CHUNK_SIZE,
            usecols=usecols,
        )
        try:
            yield from pd.read_csv(file_path, on_bad_lines="skip", **read_kwargs)
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}", file=file_path)
            logger.info("Trying with Python engine as fallback", file=file_path)
            yield from pd.read_csv(file_path, engine="python", **read_kwargs)

    def extract_fields(self):
        file_path = os.path.join(self.distribution_path, self.file_object)
        logger.info("Extracting fields from CSV file", file=file_path)

        delimiter = self._detect_delimiter(file_path)
        column_names = self._read_column_names(file_path, delimiter)
        if not column_names:
            return []

        accumulators = {col: _ColumnAccumulator() for col in column_names}

        # Pass 1: stream the whole file once, updating every column's
        # accumulator with each chunk.
        for chunk in self._iter_chunks(file_path, delimiter):
            for column in column_names:
                if column in chunk.columns:
                    accumulators[column].update(chunk[column])

        # Pass 2: the histogram bins need the global min/max gathered above, so
        # numeric columns get a second streamed pass to count per-bin frequencies.
        numeric_columns = [
            col for col, acc in accumulators.items() if acc.needs_histogram()
        ]
        if numeric_columns:
            for chunk in self._iter_chunks(file_path, delimiter, usecols=numeric_columns):
                for column in numeric_columns:
                    if column in chunk.columns:
                        accumulators[column].update_histogram(chunk[column])

        return [
            TableColumnField.from_accumulator(
                column, accumulators[column], self.name, self.file_object_id
            )
            for column in column_names
        ]

    def extract_examples(self):
        file_path = os.path.join(self.distribution_path, self.file_object)
        logger.info("Extracting examples from CSV file", file=file_path)

        delimiter = self._detect_delimiter(file_path)
        # Only the first 30 rows are needed for examples, so read just those
        # instead of materializing the whole file.
        try:
            csv_object = pd.read_csv(
                file_path,
                encoding="ISO-8859-1",
                sep=delimiter,
                nrows=30,
                on_bad_lines='skip',
            )
        except pd.errors.EmptyDataError:
            logger.warning("Empty CSV given. Skipping...", file=file_path)
            return {}

        # Convert NaN values to None in the examples dictionary
        examples_dict = csv_object.to_dict(orient="list")
        for key in examples_dict:
            examples_dict[key] = [None if pd.isna(x) else x for x in examples_dict[key]]
        return examples_dict


    def extract_data_quality(self) -> DataQualityResult | None:
        """Run LLM-based error detection on the table (detection only).

        Opt-in via the ENABLE_DATA_QUALITY env var. Any failure is logged and
        swallowed so data quality issues can never break profile generation.
        """
        if not is_data_quality_enabled() or not self.fields:
            return None

        file_path = os.path.join(self.distribution_path, self.file_object)
        try:
            delimiter = self._detect_delimiter(file_path)
            return detect_data_quality_errors(
                file_path,
                table_name=Path(self.name).name,
                delimiter=delimiter,
            )
        except Exception as e:
            logger.error(
                f"Data quality detection failed: {str(e)}", file=file_path
            )
            return None

    def to_dict(self):
        record_set_dict = {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": Path(self.name).name,
            # "description": self.description,
            # "key": self.key,
            "field": [field.to_dict() for field in self.fields],
            "examples": json.dumps(self.examples, default=str),
        }
        if self.data_quality is not None:
            record_set_dict["dataQuality"] = self.data_quality.to_dict()
        return record_set_dict

    def to_dict_cdd(self):
        record_set_dict = {
            "file_object_id": self.file_object_id,
            "original_format": "csv",
            "source_file": os.path.join(self.distribution_path, self.file_object),
            "name": Path(self.name).name,
            "description": "",
            "keywords": [],
            "columns": [field.to_dict_cdd() for field in self.fields],
        }
        if self.data_quality is not None:
            record_set_dict["data_quality"] = self.data_quality.to_dict_cdd()
        return record_set_dict

class TableColumnField(ColumnField):
    def __init__(
        self,
        column_name: str,
        data_type: str,
        sample: list,
        statistics: ColumnStatistics,
        csv_name: str,
        file_object_id: str,
    ):
        self.type = "cr:Field"
        self.id = str(uuid.uuid4())
        self.name = column_name
        self.description = ""
        self.dataType = data_type
        self.source = {
            "fileObject": {"@id": file_object_id},
            "extract": {"column": column_name},
        }
        self.sample = sample
        self.statistics: ColumnStatistics = statistics

    @classmethod
    def from_accumulator(
        cls,
        column_name: str,
        accumulator: _ColumnAccumulator,
        csv_name: str,
        file_object_id: str,
    ) -> "TableColumnField":
        return cls(
            column_name,
            accumulator.data_type(),
            accumulator.sample(),
            accumulator.build_statistics(),
            csv_name,
            file_object_id,
        )

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
