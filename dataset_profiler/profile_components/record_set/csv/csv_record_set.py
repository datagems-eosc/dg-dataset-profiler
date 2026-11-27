import csv
import json
import sys
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd
import uuid

from dataset_profiler.data_quality import (
    detect_data_quality_errors,
    is_data_quality_enabled,
)
from dataset_profiler.data_quality.models import DataQualityResult
from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.csv.calculate_statistics import (
    DATA_TYPES,
    NA_TOKENS,
    NUMERIC,
    FileBudget,
    Reservoir,
    TypeClassifier,
    _ColumnAccumulator,
    convert,
    kind_family,
    sample_seed,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    RecordSet,
    ColumnField,
)
from dataset_profiler.profile_components.cta import ColumnTypeAnnotator
from dataset_profiler.profile_components.distribution import get_original_format
from dataset_profiler.utilities import file_sha256 as compute_file_sha256, resolve_encoding
from dataset_profiler.configs.config_logging import logger

# Cells per streamed chunk of the typed (pandas) pass: wide files get fewer rows
# per chunk, so peak memory stays bounded whatever the file's shape.
CHUNK_CELLS = 2_000_000
MIN_CHUNK_ROWS = 1_000
# Cells and characters per block of the string pass, so long-text columns don't
# make blocks huge.
STRING_BLOCK_CELLS = 500_000
STRING_BLOCK_CHARS = 32_000_000
# Line numbers recorded per kind of malformed row.
REPORTED_LINES = 10
# Rows sampled for semantic type annotation. The annotator only looks at a
# handful of values per column, and its database path samples with LIMIT 100,
# so reading a bounded sample keeps CSV annotation consistent with that and
# avoids materializing the whole file.
CTA_SAMPLE_ROWS = 100
# Characters read when sniffing a file's delimiter. 1KB proved too little: files
# with long rows (URIs, non-Latin text) yield only a handful of lines, the last
# one cut short, and a partial row breaks the Sniffer's consistency check.
DELIMITER_SAMPLE_CHARS = 64 * 1024
# The only characters accepted as column separators. Unrestricted, the Sniffer
# takes any character with a steady count per row -- it picked the letter "n"
# for an ESCO file of URIs, splitting "originalSkillUri" into "origi" and
# "alSkillUri".
CANDIDATE_DELIMITERS = ",;\t|"

# Fields as long as the file allows; the csv module's default is 128 KiB.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def rows_per_chunk(n_columns: int) -> int:
    """Rows per chunk of the typed pass, bounded by ``CHUNK_CELLS``."""
    return max(MIN_CHUNK_ROWS, CHUNK_CELLS // max(n_columns, 1))


@dataclass
class StringPass:
    """What the ``csv.reader`` pass learns from the raw strings of a file."""

    header: list
    kinds: list
    samples: list
    rows: int = 0
    skipped: int = 0
    skipped_lines: list = field(default_factory=list)
    padded: int = 0
    padded_lines: list = field(default_factory=list)


def string_pass(file_path: str, encoding: str, delimiter: str, file_sha256: str,
                names: list, seed_prefix: str = "") -> StringPass:
    """Column types, seeded samples and malformed-row counts, from the raw strings.

    ``names`` are the column names as pandas reads them; each column's sample is
    seeded from ``file_sha256`` and ``seed_prefix + name``.

    Malformed rows are counted the way pandas treats them (``on_bad_lines="skip"``):
    a row with more fields than the header is skipped, a shorter one is kept and
    padded with missing values, and a blank line is ignored. Line numbers are
    physical lines, so they stay right when a quoted value holds a newline.
    """
    with open(file_path, "r", encoding=encoding, newline="") as handle:
        rows = csv.reader(handle, delimiter=delimiter)
        header = next((row for row in rows if row), [])
        width = len(header)
        classifiers = [TypeClassifier() for _ in range(width)]
        reservoirs = [Reservoir(sample_seed(file_sha256, seed_prefix + str(name))) for name in names[:width]]
        reservoirs += [
            Reservoir(sample_seed(file_sha256, f"{seed_prefix}#{i}")) for i in range(len(reservoirs), width)
        ]
        result = StringPass(header=header, kinds=[], samples=[])
        na = NA_TOKENS
        block_rows = max(MIN_CHUNK_ROWS, STRING_BLOCK_CELLS // max(width, 1))
        block: list = []
        block_chars = 0

        def flush():
            # Columns of the block, transposed at C speed; values in file order.
            for column, classifier, reservoir in zip(zip(*block), classifiers, reservoirs):
                values = [v for v in column if v not in na]
                classifier.add_many(values)
                reservoir.add_many(values)
            block.clear()

        for row in rows:
            n = len(row)
            if n == 0:
                continue   # a blank line; pandas ignores it too
            if n > width:
                # pandas skips rows with more fields than the header.
                result.skipped += 1
                if len(result.skipped_lines) < REPORTED_LINES:
                    result.skipped_lines.append(rows.line_num)
                continue
            if n < width:
                # pandas keeps short rows and fills the rest with missing values.
                result.padded += 1
                if len(result.padded_lines) < REPORTED_LINES:
                    result.padded_lines.append(rows.line_num)
                row = row + [""] * (width - n)
            result.rows += 1
            block.append(row)
            block_chars += sum(map(len, row))
            if len(block) >= block_rows or block_chars >= STRING_BLOCK_CHARS:
                flush()
                block_chars = 0
        if block:
            flush()
    result.kinds = [c.kind for c in classifiers]
    result.samples = [r.items for r in reservoirs]
    return result


class CSVRecordSet(RecordSet):
    def __init__(self, distribution_path: str, file_object: str, file_object_id: str,
                 file_sha256: Optional[str] = None, seed_prefix: str = ""):
        """``file_sha256`` is the content hash of the file the record set comes
        from (for an Excel sheet, of the workbook); it seeds the samples, and is
        computed from the file when not given. ``seed_prefix`` tells apart the
        sheets of one workbook."""
        super().__init__()
        self.distribution_path = distribution_path
        self.file_object = file_object
        self.file_object_id = file_object_id
        self.type = "cr:RecordSet"
        self._encoding = None
        self._file_sha256 = file_sha256
        self.seed_prefix = seed_prefix
        self.name = file_object.split(".")[-2]
        self.description = ""
        # Filled by extract_fields: malformed rows, approximate quantiles and
        # columns left without a uniqueCount. Logged, not part of the profile.
        self.report: dict = {}
        self.fields = self.extract_fields()
        self.examples = self.extract_examples()
        self.data_quality = self.extract_data_quality()

    @property
    def encoding(self):
        """The encoding for this record set's file, resolved once and cached.

        Resolved lazily rather than in ``__init__`` so that a missing file still
        raises from ``_detect_delimiter``, which reports it properly.
        """
        if self._encoding is None:
            self._encoding = resolve_encoding(
                os.path.join(self.distribution_path, self.file_object)
            )
            logger.info(
                "Resolved CSV encoding",
                encoding=self._encoding,
                file=self.file_object,
            )
        return self._encoding

    @property
    def file_sha256(self) -> str:
        if self._file_sha256 is None:
            self._file_sha256 = compute_file_sha256(
                os.path.join(self.distribution_path, self.file_object)
            )
        return self._file_sha256

    def _detect_delimiter(self, file_path):
        """Detect the CSV delimiter by sniffing the start of the file."""
        if not os.path.exists(file_path):
            logger.error("CSV file not found", file=file_path)
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        with open(file_path, 'r', encoding=self.encoding, newline='') as csvfile:
            sample = csvfile.read(DELIMITER_SAMPLE_CHARS)

        # Only trim when the read stopped at the limit: then the last row is
        # almost certainly cut short. A shorter file was read whole, and dropping
        # its last line would throw away a complete row.
        if len(sample) == DELIMITER_SAMPLE_CHARS and "\n" in sample:
            sample = sample[: sample.rfind("\n") + 1]

        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=CANDIDATE_DELIMITERS).delimiter
            logger.info("Detected CSV delimiter", delimiter=delimiter, file=file_path)
        except csv.Error:
            # If sniffer fails, fall back to a comma
            delimiter = ','
            logger.info("Using default CSV delimiter", delimiter=delimiter, file=file_path)
        return delimiter

    def _read_column_names(self, file_path, delimiter):
        """Read only the header row to get the column names (no data loaded)."""
        try:
            header = pd.read_csv(
                file_path, encoding=self.encoding, sep=delimiter, nrows=0
            )
        except pd.errors.EmptyDataError:
            logger.warning("Empty CSV given. Skipping...", file=file_path)
            return []
        return list(header.columns)

    def _iter_chunks(self, file_path, delimiter, usecols=None, dtype=None, chunk_rows=None):
        """Yield the CSV in row chunks, falling back to the Python engine.

        Streaming in chunks keeps peak memory bounded to a chunk instead of the
        whole file, while still reading every row exactly once per pass.
        ``dtype`` reads the named columns as given (``str`` for the columns the
        string pass found not to be numeric); the others keep pandas' types.
        """
        read_kwargs = dict(
            encoding=self.encoding,
            sep=delimiter,
            chunksize=chunk_rows or rows_per_chunk(len(usecols) if usecols else 1),
            usecols=usecols,
            dtype=dtype,
        )
        try:
            yield from pd.read_csv(file_path, on_bad_lines="skip", **read_kwargs)
        except Exception as e:
            logger.error("Error reading CSV file", error=str(e), file=file_path)
            logger.info("Trying with Python engine as fallback", file=file_path)
            yield from pd.read_csv(file_path, engine="python", **read_kwargs)

    def extract_fields(self):
        file_path = os.path.join(self.distribution_path, self.file_object)
        logger.info("Extracting fields from CSV file", file=file_path)

        delimiter = self._detect_delimiter(file_path)
        column_names = self._read_column_names(file_path, delimiter)
        if not column_names:
            return []

        columns = compute_csv_columns(self, file_path, delimiter, column_names,
                                      self.file_sha256, self.seed_prefix)
        self.report = columns.report
        stype_annotations = self._annotate_semantic_types(file_path, delimiter)

        return [
            TableColumnField(
                column,
                columns.data_types[column],
                columns.samples[column],
                columns.accumulators[column].build_statistics(),
                self.name,
                self.file_object_id,
                stype_annotations.get(column, ""),
            )
            for column in column_names
        ]

    def _annotate_semantic_types(self, file_path, delimiter) -> dict:
        """Annotate column semantic types with the LLM-backed annotator.

        The annotator needs only a sample of values per column, so a bounded
        read is used rather than the whole file. A failure here (unreachable
        LLM, auth error) is logged and swallowed: semantic types are an
        enrichment, and losing them must not fail the whole profile.
        """
        try:
            sample = pd.read_csv(
                file_path,
                encoding=self.encoding,
                sep=delimiter,
                nrows=CTA_SAMPLE_ROWS,
                on_bad_lines="skip",
            )
        except pd.errors.EmptyDataError:
            return {}
        except Exception as e:
            logger.error(
                "Failed to read sample for semantic type annotation",
                error=str(e),
                file=file_path,
            )
            return {}

        try:
            return ColumnTypeAnnotator().annotate_columns(df=sample)
        except Exception as e:
            logger.error(
                "Semantic type annotation failed", error=str(e), file=file_path
            )
            return {}

    def extract_examples(self):
        file_path = os.path.join(self.distribution_path, self.file_object)
        logger.info("Extracting examples from CSV file", file=file_path)

        delimiter = self._detect_delimiter(file_path)
        # Only the first 30 rows are needed for examples, so read just those
        # instead of materializing the whole file.
        try:
            csv_object = pd.read_csv(
                file_path,
                encoding=self.encoding,
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
                encoding=self.encoding,
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
            "examples": json.dumps(self.examples, default=str, ensure_ascii=False),
        }
        if self.data_quality is not None:
            record_set_dict["dataQuality"] = self.data_quality.to_dict()
        return record_set_dict

    def to_dict_cdd(self):
        # Data quality is deliberately absent here: it is reported only in the
        # heavy MoMa profile, not in the CDD profile.
        return {
            "file_object_id": self.file_object_id,
            "original_format": get_original_format(self.file_object),
            "source_file": os.path.join(self.distribution_path, self.file_object),
            "name": Path(self.name).name,
            "description": "",
            "keywords": [],
            "columns": [field.to_dict_cdd() for field in self.fields],
        }


@dataclass
class CSVColumns:
    """Per-column results of :func:`compute_csv_columns`, keyed by column name."""

    accumulators: dict
    data_types: dict
    samples: dict
    report: dict


def compute_csv_columns(reader, file_path: str, delimiter: str, column_names: list,
                        file_sha256: str, seed_prefix: str = "") -> CSVColumns:
    """Types, samples and statistics of every column of a CSV file.

    ``reader`` supplies ``encoding`` and ``_iter_chunks`` (a :class:`CSVRecordSet`).
    The file is read three times, each streamed:

    1. the string pass (``csv.reader``) types each column from its raw strings,
       keeps a seeded sample of them and counts malformed rows;
    2. the typed pass (pandas, in chunks sized by cells) gathers the statistics.
       Numeric columns keep pandas' types; the others are read as ``str``, so a
       column such as ``01234`` keeps its leading zeros;
    3. the histogram pass bins numeric and boolean columns once their min and
       max are known.
    """
    strings = string_pass(file_path, reader.encoding, delimiter, file_sha256,
                          column_names, seed_prefix)
    width = len(strings.header)
    if len(column_names) != width:
        logger.warning("pandas and csv.reader disagree on the number of columns",
                       file=file_path, pandas_columns=len(column_names), header_fields=width)
    kinds = {
        name: (strings.kinds[i] if i < width else None)
        for i, name in enumerate(column_names)
    }
    families = {name: kind_family(kind) for name, kind in kinds.items()}

    budget = FileBudget()
    accumulators = {name: _ColumnAccumulator(families[name], budget) for name in column_names}
    dtype = {name: str for name, family in families.items() if family != NUMERIC}
    chunk_rows = rows_per_chunk(len(column_names))

    for chunk in reader._iter_chunks(file_path, delimiter, dtype=dtype or None, chunk_rows=chunk_rows):
        for name in column_names:
            if name in chunk.columns:
                accumulators[name].update(chunk[name])

    binned = [name for name, acc in accumulators.items() if acc.needs_histogram()]
    if binned:
        binned_dtype = {name: t for name, t in dtype.items() if name in binned}
        for chunk in reader._iter_chunks(file_path, delimiter, usecols=binned,
                                         dtype=binned_dtype or None, chunk_rows=chunk_rows):
            for name in binned:
                if name in chunk.columns:
                    accumulators[name].update_histogram(chunk[name])

    samples = {
        name: [convert(v, kinds[name]) for v in (strings.samples[i] if i < width else [])]
        for i, name in enumerate(column_names)
    }
    report = {
        "rows": strings.rows,
        "skipped_rows": strings.skipped,
        "skipped_lines": strings.skipped_lines,
        "padded_rows": strings.padded,
        "padded_lines": strings.padded_lines,
        "approximate_quantiles": [n for n, acc in accumulators.items() if acc.approximate],
        "unique_count_dropped": [n for n, acc in accumulators.items() if acc.unique_dropped],
    }
    _log_report(file_path, report)
    return CSVColumns(
        accumulators=accumulators,
        data_types={name: DATA_TYPES[kind] for name, kind in kinds.items()},
        samples=samples,
        report=report,
    )


def _log_report(file_path: str, report: dict):
    if report["skipped_rows"]:
        logger.warning(
            "Malformed CSV rows with more fields than the header were skipped",
            file=file_path, count=report["skipped_rows"], lines=report["skipped_lines"],
        )
    if report["padded_rows"]:
        logger.info(
            "CSV rows with fewer fields than the header were padded with missing values",
            file=file_path, count=report["padded_rows"], lines=report["padded_lines"],
        )
    if report["approximate_quantiles"]:
        logger.info(
            "Quantiles are t-digest estimates: the file holds more numeric values than are kept exactly",
            file=file_path, columns=report["approximate_quantiles"],
        )
    if report["unique_count_dropped"]:
        logger.info(
            "uniqueCount left null: too many distinct values to count exactly",
            file=file_path, columns=report["unique_count_dropped"],
        )


class TableColumnField(ColumnField):
    def __init__(
        self,
        column_name: str,
        data_type: str,
        sample: list,
        statistics: ColumnStatistics,
        csv_name: str,
        file_object_id: str,
        semantic_type: Optional[str] = "",
    ):
        self.type = "cr:Field"
        self.id = str(uuid.uuid4())
        self.name = column_name
        self.description = ""
        self.dataType = data_type
        self.semanticType = semantic_type
        self.source = {
            "fileObject": {"@id": file_object_id},
            "extract": {"column": column_name},
        }
        self.sample = sample
        self.statistics: ColumnStatistics = statistics

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "dataType": self.dataType,      # dataType for core profile and primitive_type for CDD?
            "semanticType": self.semanticType,
            "source": self.source,
            "sample": self.sample,
            "statistics": self.statistics.to_dict(),
        }

    def to_dict_cdd(self):
        return {
            "name": self.name,
            "primitive_type": self.dataType,
            "semantic_type": self.semanticType,
            "description": self.description,
            "statistics": self.statistics.to_dict_cdd(),
        }


def get_record_sets_from_excel(
    distribution_path: str, file_object: str, file_object_id: str,
    file_sha256: Optional[str] = None,
) -> list[CSVRecordSet]:
    """One record set per non-empty sheet, each with the FileObject of its own sheet.

    ``file_sha256`` is the workbook's content hash (computed when not given);
    each sheet's samples are seeded from it and the sheet's name.
    """
    workbook_path = os.path.join(distribution_path, file_object)
    if file_sha256 is None:
        file_sha256 = compute_file_sha256(workbook_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        xls = pd.ExcelFile(workbook_path)
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
                    file_sha256=file_sha256,
                    seed_prefix=f"{sheet_name}\0",
                )
            except (pd.errors.ParserError, csv.Error) as e:
                # print the stack trace for debugging purposes
                logger.warning(
                    f"Failed to process sheet {sheet_name} in {file_object} with error {e}. Skipping this sheet."
                )
                continue
            # Named after the sheet actually profiled. (Pairing record sets with
            # sheet names afterwards shifted every name after a skipped sheet.)
            record_set.inject_distribution = {
                "@type": "cr:FileObject",
                "@id": str(uuid.uuid4()),
                "name": sheet_name,
                "description": "",
                "containedIn": {"@id": file_object_id},
                "encodingFormat": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            record_sets.append(record_set)

    return record_sets
