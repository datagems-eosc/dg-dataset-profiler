"""Record sets for JSON and JSON Lines files.

A JSON file is profiled as a table whose columns are JSONPaths. The profiler
first works out where the records are (the *record path*), then streams every
record once, flattening it into leaf paths such as ``location.lat`` or
``readings[*].temp_c`` and feeding each path's values into the same
:class:`_ColumnAccumulator` the CSV profiler uses. A second streamed pass bins
the numeric paths into histograms, exactly as for CSV.

Statistics mean the same as for CSV columns: a record where a key is absent
counts as missing, just like one where it is ``null``. For a path under an
array (``repeated``) the counts are over array elements rather than records.

Files are never loaded whole: JSON is parsed incrementally with ``ijson`` and
JSON Lines line by line, so memory stays bounded whatever the file size.
"""

import codecs
import io
import json
import math
import os
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import ijson
import pandas as pd

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.profile_components.cta import ColumnTypeAnnotator
from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
from dataset_profiler.profile_components.record_set.csv.calculate_statistics import (
    _ColumnAccumulator,
)
from dataset_profiler.profile_components.record_set.document_description import (
    describe_document,
)
from dataset_profiler.profile_components.record_set.record_set_abc import (
    ColumnField,
    RecordSet,
)
from dataset_profiler.profile_components.record_set.text.text_utilities import (
    chunk_text_by_paragraph,
)
from dataset_profiler.utilities import resolve_encoding

JSON_LINES_SUFFIXES = {".jsonl", ".ndjson"}
JSON_SUFFIXES = {".json", ".geojson"} | JSON_LINES_SUFFIXES

# Layouts a file can have; see dg:jsonShape in datagems-croissant-extension.ttl.
ARRAY_OF_RECORDS = "array_of_records"
JSON_LINES = "json_lines"
WRAPPED_RECORDS = "wrapped_records"
SINGLE_DOCUMENT = "single_document"
INVALID = "invalid"

# Parser events read while looking for the records. Enough for any realistic
# header before the record array, without scanning a large file twice.
DETECT_EVENT_LIMIT = 1_000_000
# Records read up front to spot objects used as maps (see _detect_map_paths).
MAP_DETECT_RECORDS = 1_000
# A nested object with more distinct keys than this, each appearing in only a
# small share of the objects, is a map ({"2019": …, "2020": …}): its keys are
# data, and listing each as a field would explode the field count.
MAP_MIN_KEYS = 50
MAP_MAX_MEDIAN_KEY_SHARE = 0.10
# ... or with at least this many distinct keys, nearly all of which look like
# values rather than names: dates, numbers, UUIDs, hex ids.
MAP_MIN_DATA_KEYS = 10
MAP_MIN_DATA_KEY_SHARE = 0.9
_DATA_KEY = re.compile(
    r"^(\d{4}-\d{2}(-\d{2})?([T ][\d:.]+Z?)?"      # dates and timestamps
    r"|-?\d+(\.\d+)?"                            # numbers
    r"|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|[0-9a-fA-F]{16,})$"                          # hex ids and hashes
)
# Bounds on the schema. Paths beyond MAX_PATHS are dropped (paths_truncated);
# containers nested deeper than MAX_DEPTH become a single opaque field.
MAX_PATHS = 300
MAX_DEPTH = 8
# Values buffered per path before being handed to the accumulators.
FLUSH_EVERY = 10_000
# Flattened records sent to the semantic type annotator, as for CSV.
CTA_SAMPLE_RECORDS = 100
EXAMPLE_RECORDS = 3
EXAMPLE_LIST_ITEMS = 3
EXAMPLE_STRING_CHARS = 200
MAX_METADATA_ENTRIES = 20
MAX_METADATA_VALUE_CHARS = 200
# Most frequent values are reported for fields with at most this many distinct
# values; beyond it they are not useful as search facets.
TOP_VALUES = 10
TOP_VALUES_MAX_UNIQUE = 50
TOP_VALUES_TRACK_CAP = 1_000
# Text fields averaging at least this many characters are chunked into
# chunked_content so semantic search reaches inside them.
LONG_TEXT_MIN_AVG_CHARS = 120
LONG_TEXT_STORE_MIN_CHARS = 60
MAX_STORED_TEXT_CHARS = 5_000_000
MAX_TEXT_CHUNKS = 2_000
TEXT_CHUNK_SIZE = 300
TEXT_CHUNK_OVERLAP = 20
# Top-level keys whose value names a record in chunked_content.
RECORD_LABEL_KEYS = ("id", "_id", "uuid", "key", "name", "title")
# The schema rendered for the LLM summary is capped at this many fields.
SUMMARY_MAX_FIELDS = 60

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"
)

# Path components. A relative path is a tuple of them, e.g.
# (("key", "readings"), ITEM, ("key", "temp_c")) for readings[*].temp_c.
ITEM = ("item",)
WILDCARD = ("key", "*")

NUMERIC, BOOLEAN, TEXT = "numeric", "boolean", "text"


def is_json_record_sets_enabled() -> bool:
    """JSON record sets in the heavy profile; ENABLE_JSON_RECORD_SETS=false drops them."""
    return os.environ.get("ENABLE_JSON_RECORD_SETS", "true").lower() in (
        "1", "true", "yes", "on",
    )


def is_json_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in JSON_SUFFIXES


# =============================================================================
# Reading
# =============================================================================

class _Utf8Reader(io.RawIOBase):
    """Byte stream of a text file re-encoded as UTF-8, for ijson.

    ijson only reads UTF-8 bytes. The rare JSON file in another encoding (a
    cp1252 export, say) is decoded and re-encoded on the fly rather than loaded.
    """

    def __init__(self, path: str, encoding: str):
        self._text = open(path, "r", encoding=encoding, newline="")
        self._pending = b""

    def readable(self):
        return True

    def readinto(self, buffer):
        while not self._pending:
            chunk = self._text.read(64 * 1024)
            if not chunk:
                return 0
            self._pending = chunk.encode("utf-8")
        n = min(len(buffer), len(self._pending))
        buffer[:n] = self._pending[:n]
        self._pending = self._pending[n:]
        return n

    def close(self):
        self._text.close()
        super().close()


def _open_utf8(path: str, encoding: str):
    """Binary UTF-8 stream of the file, with any byte-order mark skipped."""
    if encoding in ("utf-8-sig", "utf-8"):
        handle = open(path, "rb")
        if handle.read(len(codecs.BOM_UTF8)) != codecs.BOM_UTF8:
            handle.seek(0)
        return handle
    return io.BufferedReader(_Utf8Reader(path, encoding))


# =============================================================================
# Structure detection
# =============================================================================

@dataclass
class _Structure:
    shape: str
    record_path: str = "$"
    # ijson prefix of one record, e.g. "stations.item"; None for JSON Lines.
    ijson_prefix: Optional[str] = None
    dialect: Optional[str] = None
    document_metadata: dict = field(default_factory=dict)
    parse_errors: int = 0


def _render_path(base: str, components) -> str:
    """JSONPath string for components appended to ``base`` (e.g. "$")."""
    out = base
    for comp in components:
        if comp == ITEM:
            out += "[*]"
        elif comp == WILDCARD:
            out += ".*"
        else:
            key = comp[1]
            if _IDENTIFIER.match(key):
                out += "." + key
            else:
                out += "['" + key.replace("\\", "\\\\").replace("'", "\\'") + "']"
    return out


def _display_name(components) -> str:
    """Relative field name as shown to people: location.lat, readings[*].temp_c."""
    out = ""
    for comp in components:
        if comp == ITEM:
            out += "[*]"
        else:
            out += ("." if out else "") + comp[1]
    return out or "value"


def _looks_like_json_lines(path: str, encoding: str) -> bool:
    """A .json file that is really JSON Lines: first two non-empty lines each parse alone."""
    parsed = 0
    with open(path, "r", encoding=encoding, errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except ValueError:
                return False
            parsed += 1
            if parsed == 2:
                return True
    return False


def _detect_structure(path: str, encoding: str, is_lines: bool) -> _Structure:
    """Find where the records are, and the file's dialect and metadata."""
    if is_lines:
        return _Structure(shape=JSON_LINES, record_path="$")

    frames: list[dict] = []          # open containers: {"kind", "base", "key"}
    array_counts: Counter = Counter()  # array path -> objects directly inside it
    array_prefixes: dict = {}         # array path -> ijson prefix of its items
    root_kind = None
    root_keys: set = set()
    root_type_value = None
    metadata: dict = {}

    def position():
        if not frames:
            return ()
        top = frames[-1]
        if top["kind"] == "map":
            return top["base"] + (("key", top["key"]),)
        return top["base"] + (ITEM,)

    try:
        with _open_utf8(path, encoding) as handle:
            for n, (prefix, event, value) in enumerate(ijson.parse(handle, use_float=True)):
                if n >= DETECT_EVENT_LIMIT:
                    break
                if event == "map_key":
                    frames[-1]["key"] = value
                    if len(frames) == 1:
                        root_keys.add(value)
                    continue
                if event in ("end_map", "end_array"):
                    frames.pop()
                    continue
                pos = position()
                if root_kind is None:
                    root_kind = event
                if event in ("start_map", "start_array"):
                    if event == "start_map" and frames and frames[-1]["kind"] == "array":
                        array_path = frames[-1]["base"]
                        array_counts[array_path] += 1
                        array_prefixes.setdefault(array_path, prefix)
                    frames.append({
                        "kind": "map" if event == "start_map" else "array",
                        "base": pos,
                        "key": None,
                    })
                    continue
                # A scalar.
                if pos == (("key", "type"),):
                    root_type_value = value
                if (
                    pos and ITEM not in pos
                    and len(metadata) < MAX_METADATA_ENTRIES
                ):
                    text = value if isinstance(value, str) else json.dumps(value)
                    metadata[_render_path("$", pos)] = text[:MAX_METADATA_VALUE_CHARS]
    except ijson.JSONError as e:
        if _looks_like_json_lines(path, encoding):
            logger.info("JSON file holds one document per line, reading it as JSON Lines",
                        file=path)
            return _Structure(shape=JSON_LINES, record_path="$")
        if root_kind is None:
            logger.warning("Invalid JSON, profiling the file without fields",
                           file=path, error=str(e)[:300])
            return _Structure(shape=INVALID, parse_errors=1)
        # The file breaks off after its structure was clear (a truncated
        # download, say): profile the records before the break.
        logger.warning("JSON file is invalid part-way, profiling it up to the error",
                       file=path, error=str(e)[:300])
        parse_errors = 1
    else:
        parse_errors = 0

    dialect = _dialect(root_keys, root_type_value)

    if root_kind == "start_array":
        return _Structure(shape=ARRAY_OF_RECORDS, record_path="$[*]",
                          ijson_prefix="item", dialect=dialect, parse_errors=parse_errors)
    if root_kind == "start_map" and array_counts:
        # The outermost array of objects wins: stations, not stations.readings,
        # even though the readings outnumber the stations. Among several at the
        # same nesting, the one with the most objects.
        chosen = min(
            array_counts,
            key=lambda p: (sum(1 for c in p if c == ITEM), -array_counts[p], len(p)),
        )
        # Metadata holds only scalars outside every array, so none of it comes
        # from inside the records.
        return _Structure(shape=WRAPPED_RECORDS,
                          record_path=_render_path("$", chosen) + "[*]",
                          ijson_prefix=array_prefixes[chosen], dialect=dialect,
                          document_metadata=metadata, parse_errors=parse_errors)
    # An object with no array of objects in it (a config, a report), or a bare
    # scalar: the whole document is the one record.
    return _Structure(shape=SINGLE_DOCUMENT, record_path="$", ijson_prefix="",
                      dialect=dialect, parse_errors=parse_errors)


def _dialect(root_keys: set, root_type_value) -> Optional[str]:
    if root_type_value in ("FeatureCollection", "Feature"):
        return "geojson"
    if "@context" in root_keys:
        return "json-ld"
    if "$schema" in root_keys:
        return "json-schema"
    if "openapi" in root_keys or "swagger" in root_keys:
        return "openapi"
    return None


# =============================================================================
# Per-path accumulation
# =============================================================================

def _is_map(key_counts: Counter, n_objects: int) -> bool:
    """Whether the keys seen under one object path are data rather than field names."""
    distinct = len(key_counts)
    if distinct >= MAP_MIN_DATA_KEYS:
        data_like = sum(1 for k in key_counts if _DATA_KEY.match(k))
        if data_like / distinct >= MAP_MIN_DATA_KEY_SHARE:
            return True
    if distinct > MAP_MIN_KEYS:
        shares = sorted(n / n_objects for n in key_counts.values())
        if shares[len(shares) // 2] < MAP_MAX_MEDIAN_KEY_SHARE:
            return True
    return False


def _json_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number" if math.isfinite(value) else "null"
    if isinstance(value, str):
        return "string"
    return "object" if isinstance(value, dict) else "array"


class _PathAccumulator:
    """Everything gathered for one leaf path.

    Values are split by family -- numbers, booleans, text -- and each family
    feeds its own :class:`_ColumnAccumulator`. The field's statistics come from
    the family holding most of its values, so a number field with a dozen
    ``"n/a"`` strings still gets a mean and a histogram; the minority values are
    reported through ``jsonTypes`` (mixed types) and left out of the numbers.
    """

    def __init__(self):
        self.types: Counter = Counter()
        self._buffers = {NUMERIC: [], BOOLEAN: [], TEXT: []}
        self.accumulators: dict = {}
        self.top: Counter = Counter()
        self.top_capped = False
        self.text_chars = 0
        self.texts: list = []          # (record label, text) of long strings

    def add(self, value, store_text: bool, label: str):
        kind = _json_type(value)
        self.types[kind] += 1
        if kind == "null":
            return
        if kind == "boolean":
            family = BOOLEAN
        elif kind in ("integer", "number"):
            family = NUMERIC
        else:
            family = TEXT
            if kind != "string":   # a container cut off at MAX_DEPTH
                value = json.dumps(value, ensure_ascii=False)
            self.text_chars += len(value)
            if store_text and len(value) >= LONG_TEXT_STORE_MIN_CHARS:
                self.texts.append((label, value))
        self._buffers[family].append(value)
        if family != NUMERIC and not self.top_capped:
            self.top[value] += 1
            if len(self.top) > TOP_VALUES_TRACK_CAP:
                self.top_capped = True
                self.top.clear()
        if len(self._buffers[family]) >= FLUSH_EVERY:
            self._flush(family)

    def add_histogram_value(self, value):
        if _json_type(value) in ("integer", "number"):
            self._buffers[NUMERIC].append(value)
            if len(self._buffers[NUMERIC]) >= FLUSH_EVERY:
                self._flush_histogram()

    def _series(self, family: str, values: list) -> pd.Series:
        if family == NUMERIC:
            if all(isinstance(v, int) for v in values):
                try:
                    return pd.Series(values, dtype="int64")
                except OverflowError:
                    pass
            return pd.Series(values, dtype="float64")
        if family == BOOLEAN:
            return pd.Series(values, dtype=bool)
        return pd.Series(values, dtype=object)

    def _flush(self, family: str):
        values = self._buffers[family]
        if not values:
            return
        acc = self.accumulators.setdefault(family, _ColumnAccumulator())
        acc.update(self._series(family, values))
        self._buffers[family] = []

    def flush(self):
        for family in (NUMERIC, BOOLEAN, TEXT):
            self._flush(family)

    def _flush_histogram(self):
        values = self._buffers[NUMERIC]
        if values:
            self.accumulators[NUMERIC].update_histogram(self._series(NUMERIC, values))
            self._buffers[NUMERIC] = []

    def flush_histogram(self):
        self._flush_histogram()

    def is_long_text(self) -> bool:
        strings = self.types["string"]
        return bool(strings) and self.text_chars / strings >= LONG_TEXT_MIN_AVG_CHARS

    @property
    def non_null(self) -> int:
        return sum(n for kind, n in self.types.items() if kind != "null")

    def family(self) -> Optional[str]:
        counts = {
            NUMERIC: self.types["integer"] + self.types["number"],
            BOOLEAN: self.types["boolean"],
            TEXT: self.types["string"] + self.types["object"] + self.types["array"],
        }
        if not any(counts.values()):
            return None
        # Ties go to numbers, then text: their statistics say more.
        return max((NUMERIC, TEXT, BOOLEAN), key=lambda f: counts[f])

    def needs_histogram(self) -> bool:
        acc = self.accumulators.get(NUMERIC)
        return self.family() == NUMERIC and acc is not None and acc.needs_histogram()


# =============================================================================
# The record set
# =============================================================================

class JSONRecordSet(RecordSet):
    """Record set of one JSON or JSON Lines file.

    ``use_llm`` turns off the two LLM enrichments -- semantic types and the
    summary -- for files beyond the per-folder cap; everything else is computed.
    """

    def __init__(self, file_path: str, file_object_id: str, use_llm: bool = True):
        super().__init__()
        self.file_path = file_path
        self.file_object_id = file_object_id
        self.use_llm = use_llm
        self.type = "cr:RecordSet"
        self.name = Path(file_path).stem
        self.is_lines = Path(file_path).suffix.lower() in JSON_LINES_SUFFIXES
        self.encoding = resolve_encoding(file_path)

        self.record_count = 0
        self.max_depth = 0
        self.paths_truncated = False
        self.parse_errors = 0
        self._paths: dict = {}
        self._map_paths: set = set()
        self._repeat_counts: Counter = Counter()   # array/map path -> elements
        self._array_lengths: dict = {}             # array path -> [min, max, sum, n]
        self._key_sets: Counter = Counter()
        self._key_sets_capped = False
        self._cta_rows: list = []
        self._cta_row: Optional[dict] = None
        self._examples: list = []
        self._stored_text_chars = 0

        self.structure = _detect_structure(file_path, self.encoding, self.is_lines)
        if self.structure.shape == JSON_LINES:
            # A .json file found to hold JSON Lines is read as such.
            self.is_lines = True
        self.parse_errors = self.structure.parse_errors

        self.fields: list = []
        self.chunked_content: list = []
        self.summary = ""
        self.keywords: list = []
        if self.structure.shape != INVALID:
            self.fields = self.extract_fields()
            self.chunked_content = self._build_chunked_content()
            if self.use_llm:
                self._describe()
        logger.info(
            "Profiled JSON file",
            file=file_path,
            shape=self.structure.shape,
            record_path=self.structure.record_path,
            records=self.record_count,
            fields=len(self.fields),
            parse_errors=self.parse_errors,
        )

    # -- reading records -------------------------------------------------------
    def _iter_records(self, limit: Optional[int] = None, count_errors: bool = False) -> Iterator:
        """Yield records; parse errors are counted (when asked), never raised.

        Only the statistics pass counts errors: the other passes re-read the same
        file and would count each one again.
        """
        count = 0
        if self.is_lines:
            with open(self.file_path, "rb") as handle:
                for raw in handle:
                    if limit is not None and count >= limit:
                        return
                    line = raw.decode(
                        "utf-8-sig" if self.encoding.startswith("utf-8") else self.encoding,
                        errors="replace",
                    ).strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        if count_errors:
                            self.parse_errors += 1
                        continue
                    count += 1
                    yield record
            return
        try:
            with _open_utf8(self.file_path, self.encoding) as handle:
                for record in ijson.items(handle, self.structure.ijson_prefix, use_float=True):
                    if limit is not None and count >= limit:
                        return
                    count += 1
                    yield record
        except ijson.JSONError as e:
            # The file breaks off part-way: keep what was read before the error.
            if count_errors and self.parse_errors == 0:
                self.parse_errors = 1
                logger.warning("JSON file is invalid part-way, profiled up to the error",
                               file=self.file_path, records_read=count, error=str(e)[:300])

    # -- map detection -----------------------------------------------------------
    def _detect_map_paths(self):
        """Mark nested objects whose keys are data, so they collapse to one ``*`` path."""
        objects: Counter = Counter()
        keys: dict = defaultdict(Counter)

        def walk(value, rel, depth):
            if depth > MAX_DEPTH:
                return
            if isinstance(value, dict):
                if rel:   # the record itself is never a map
                    objects[rel] += 1
                    if len(keys[rel]) <= 10 * MAP_MIN_KEYS:
                        keys[rel].update(value.keys())
                for k, v in value.items():
                    walk(v, rel + (("key", k),), depth + 1)
            elif isinstance(value, list):
                for v in value:
                    walk(v, rel + (ITEM,), depth + 1)

        for record in self._iter_records(limit=MAP_DETECT_RECORDS):
            walk(record, (), 1)

        for rel, key_counts in keys.items():
            if _is_map(key_counts, objects[rel]):
                self._map_paths.add(rel)
        if self._map_paths:
            logger.info("Collapsed map-like objects to wildcard paths",
                        file=self.file_path,
                        paths=[_display_name(p) for p in self._map_paths])

    # -- pass one ------------------------------------------------------------------
    def _walk(self, value, rel, depth, label, histogram_only=False):
        if isinstance(value, (dict, list)) and depth <= MAX_DEPTH:
            if not histogram_only:
                self.max_depth = max(self.max_depth, depth)
            if isinstance(value, dict):
                collapse = rel in self._map_paths
                if collapse and not histogram_only:
                    self._repeat_counts[rel + (WILDCARD,)] += len(value)
                for k, v in value.items():
                    child = rel + (WILDCARD if collapse else ("key", k),)
                    self._walk(v, child, depth + 1, label, histogram_only)
            else:
                arr = rel + (ITEM,)
                if not histogram_only:
                    self._repeat_counts[arr] += len(value)
                    stats = self._array_lengths.setdefault(arr, [len(value), len(value), 0, 0])
                    stats[0] = min(stats[0], len(value))
                    stats[1] = max(stats[1], len(value))
                    stats[2] += len(value)
                    stats[3] += 1
                for v in value:
                    self._walk(v, arr, depth + 1, label, histogram_only)
            return
        # A leaf: a scalar, or a container cut off at MAX_DEPTH.
        if histogram_only:
            acc = self._paths.get(rel)
            if acc is not None and acc.needs_histogram():
                acc.add_histogram_value(value)
            return
        acc = self._paths.get(rel)
        if acc is None:
            if len(self._paths) >= MAX_PATHS:
                self.paths_truncated = True
                return
            acc = self._paths[rel] = _PathAccumulator()
        store = self._stored_text_chars < MAX_STORED_TEXT_CHARS
        before = len(acc.texts)
        acc.add(value, store_text=store, label=label)
        if len(acc.texts) > before:
            self._stored_text_chars += len(acc.texts[-1][1])
        if self._cta_row is not None and rel not in self._cta_row:
            self._cta_row[rel] = value

    def _record_label(self, record) -> str:
        if isinstance(record, dict):
            for key in RECORD_LABEL_KEYS:
                value = record.get(key)
                if isinstance(value, (str, int)) and not isinstance(value, bool):
                    return str(value)
        return f"record {self.record_count}"

    def extract_fields(self):
        self._detect_map_paths()

        for record in self._iter_records(count_errors=True):
            self.record_count += 1
            if isinstance(record, dict) and not self._key_sets_capped:
                self._key_sets[frozenset(record.keys())] += 1
                if len(self._key_sets) > 10_000:
                    self._key_sets_capped = True
            if len(self._examples) < EXAMPLE_RECORDS:
                self._examples.append(_preview(record))
            self._cta_row = {} if len(self._cta_rows) < CTA_SAMPLE_RECORDS else None
            if self._cta_row is not None:
                self._cta_rows.append(self._cta_row)
            self._walk(record, (), 1, self._record_label(record))
        self._cta_row = None
        for acc in self._paths.values():
            acc.flush()

        # Pass two: histograms need each numeric path's global min/max.
        if any(acc.needs_histogram() for acc in self._paths.values()):
            for record in self._iter_records():
                self._walk(record, (), 1, "", histogram_only=True)
            for acc in self._paths.values():
                if acc.needs_histogram():
                    acc.flush_histogram()

        semantic_types = self._annotate_semantic_types() if self.use_llm else {}
        return [
            JSONField.from_accumulator(
                rel=rel,
                acc=acc,
                record_path=self.structure.record_path,
                total=self._total_for(rel),
                array_length=self._array_length_for(rel),
                file_object_id=self.file_object_id,
                semantic_type=semantic_types.get(_display_name(rel), ""),
            )
            for rel, acc in self._paths.items()
        ]

    def _innermost_repeat(self, rel):
        for i in range(len(rel) - 1, -1, -1):
            if rel[i] in (ITEM, WILDCARD):
                return rel[: i + 1]
        return None

    def _total_for(self, rel) -> int:
        """Rows a path could have had: records, or elements of its innermost array."""
        repeat = self._innermost_repeat(rel)
        return self.record_count if repeat is None else self._repeat_counts[repeat]

    def _array_length_for(self, rel) -> Optional[dict]:
        repeat = self._innermost_repeat(rel)
        if repeat is None or repeat[-1] != ITEM or repeat not in self._array_lengths:
            return None
        mn, mx, total, n = self._array_lengths[repeat]
        return {"min": mn, "avg": round(total / n, 2) if n else None, "max": mx}

    # -- LLM enrichments --------------------------------------------------------------
    def _annotate_semantic_types(self) -> dict:
        """Semantic types from a sample of flattened records, as for CSV columns."""
        if not self._cta_rows or not self._paths:
            return {}
        columns = list(self._paths)
        sample = pd.DataFrame(
            [[row.get(rel) for rel in columns] for row in self._cta_rows],
            columns=[_display_name(rel) for rel in columns],
        )
        try:
            return ColumnTypeAnnotator().annotate_columns(df=sample)
        except Exception as e:  # noqa: BLE001 - an enrichment must not fail the profile
            logger.error("Semantic type annotation failed", error=str(e), file=self.file_path)
            return {}

    def _describe(self):
        """Keywords and a summary from the schema and a few records, one LLM call."""
        # The input leads with the data, not the file mechanics: given the record
        # path and layout first, the model summarised the format ("a JSON file
        # with five wrapped records under $.stations[*]") instead of the content.
        lines = [
            "Fields and sample records of a data file. Describe what the data is "
            "about -- its subject, entities and measurements -- not its file format.",
            f"Number of records: {self.record_count}.",
        ]
        if self.structure.document_metadata:
            lines.append("Metadata outside the records: "
                         + json.dumps(self.structure.document_metadata, ensure_ascii=False))
        lines.append("Fields:")
        for f in self.fields[:SUMMARY_MAX_FIELDS]:
            lines.append(f"- {f.name} ({f.data_type}) e.g. "
                         + json.dumps(f.sample[:3], ensure_ascii=False, default=str))
        lines.append("Sample records:")
        lines.extend(json.dumps(r, ensure_ascii=False, default=str) for r in self._examples)
        description = describe_document("\n".join(lines), name=Path(self.file_path).name)
        self.summary = description.summary
        self.keywords = description.keywords

    # -- content for search -----------------------------------------------------------
    def _build_chunked_content(self) -> list:
        content = []
        budget = MAX_TEXT_CHUNKS
        for rel, acc in self._paths.items():
            if not acc.is_long_text():
                continue
            for label, text in acc.texts:
                if budget <= 0:
                    return content
                chunks = chunk_text_by_paragraph(
                    text, chunk_size=TEXT_CHUNK_SIZE, chunk_overlap=TEXT_CHUNK_OVERLAP
                )[:budget]
                budget -= len(chunks)
                content.append({
                    "section": _display_name(rel),
                    "subsection": label,
                    "chunks": chunks,
                })
        return content

    # -- file-level properties ---------------------------------------------------------
    @property
    def schema_consistency_percentage(self) -> Optional[float]:
        if not self._key_sets or self.record_count == 0:
            return None
        return round(100 * max(self._key_sets.values()) / self.record_count, 2)

    def _json_profile(self) -> dict:
        return {
            "shape": self.structure.shape,
            "dialect": self.structure.dialect,
            "record_path": self.structure.record_path,
            "record_count": self.record_count,
            "max_depth": self.max_depth,
            "path_count": len(self.fields),
            "paths_truncated": self.paths_truncated,
            "schema_consistency_percentage": self.schema_consistency_percentage,
            "parse_errors": self.parse_errors,
            "summary": self.summary,
            "document_metadata": self.structure.document_metadata,
            "sample_records": json.dumps(self._examples, ensure_ascii=False, default=str),
        }

    # -- outputs -------------------------------------------------------------------------
    def to_dict(self):
        record_set = {
            "@type": self.type,
            "@id": str(uuid.uuid4()),
            "name": self.name,
            "description": self.summary,
            "summary": self.summary,
            "keywords": self.keywords,
            "recordPath": self.structure.record_path,
            "jsonShape": self.structure.shape,
            "recordCount": self.record_count,
            "maxDepth": self.max_depth,
            "schemaConsistencyPercentage": self.schema_consistency_percentage,
            "field": [f.to_dict() for f in self.fields],
            "examples": json.dumps(self._examples, ensure_ascii=False, default=str),
        }
        return record_set

    def to_dict_cdd(self):
        return {
            "file_object_id": self.file_object_id,
            "original_format": "jsonl" if self.is_lines else "json",
            "source_file": self.file_path,
            "name": self.name,
            "description": self.summary,
            "keywords": self.keywords,
            "json_profile": self._json_profile(),
            "columns": [f.to_dict_cdd() for f in self.fields],
            "chunked_content": self.chunked_content,
        }


def _preview(value, depth: int = 0):
    """A record shortened for display: lists to a few items, long strings cut."""
    if isinstance(value, dict):
        return {k: _preview(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        items = [_preview(v, depth + 1) for v in value[:EXAMPLE_LIST_ITEMS]]
        if len(value) > EXAMPLE_LIST_ITEMS:
            items.append(f"… {len(value) - EXAMPLE_LIST_ITEMS} more")
        return items
    if isinstance(value, str) and len(value) > EXAMPLE_STRING_CHARS:
        return value[:EXAMPLE_STRING_CHARS] + "…"
    return value


class JSONField(ColumnField):
    def __init__(
        self,
        name: str,
        json_path: str,
        repeated: bool,
        data_type: str,
        sample: list,
        statistics: ColumnStatistics,
        file_object_id: str,
        array_length: Optional[dict] = None,
        semantic_type: str = "",
    ):
        self.type = "cr:Field"
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = ""
        self.json_path = json_path
        self.repeated = repeated
        self.data_type = data_type
        self.semantic_type = semantic_type
        self.sample = sample
        self.statistics = statistics
        self.array_length = array_length
        self.file_object_id = file_object_id

    @classmethod
    def from_accumulator(cls, rel, acc: _PathAccumulator, record_path: str, total: int,
                         array_length: Optional[dict], file_object_id: str,
                         semantic_type: str = "") -> "JSONField":
        family = acc.family()
        non_null = acc.non_null
        missing = max(total - non_null, 0)
        missing_pct = float(missing / total * 100) if total else 0.0
        json_types = dict(
            sorted(((k, v) for k, v in acc.types.items() if k != "null"),
                   key=lambda kv: -kv[1])
        )

        if family is None:
            data_type, sample = "sc:Text", []
            statistics = ColumnStatistics(row_count=0, unique_count=0)
        else:
            chosen = acc.accumulators[family]
            sample = chosen.sample()
            if family == BOOLEAN:
                # Counted like text: a mean and histogram of true/false say less
                # than the true and false counts in topValues.
                data_type = "sc:Boolean"
                statistics = ColumnStatistics(unique_count=chosen.unique_count())
            else:
                statistics = chosen.build_statistics()
                data_type = (
                    _text_data_type(sample) if family == TEXT else chosen.data_type()
                )

        # Counts over the whole field, not just the family the statistics come
        # from: absent keys and nulls are missing, every other value is a row.
        statistics.row_count = non_null
        statistics.missing_count = missing
        statistics.missing_percentage = missing_pct
        statistics.json_types = json_types
        statistics.top_values = _top_values(acc, family, non_null)

        return cls(
            name=_display_name(rel),
            json_path=_render_path(record_path, rel),
            repeated=any(c in (ITEM, WILDCARD) for c in rel),
            data_type=data_type,
            sample=sample,
            statistics=statistics,
            file_object_id=file_object_id,
            array_length=array_length,
            semantic_type=semantic_type,
        )

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "dataType": self.data_type,
            "semanticType": self.semantic_type,
            "source": {
                "fileObject": {"@id": self.file_object_id},
                "extract": {"jsonPath": self.json_path},
            },
            "repeated": self.repeated,
            "sample": self.sample,
            "statistics": self.statistics.to_dict(),
        }

    def to_dict_cdd(self):
        column = {
            "name": self.name,
            "json_path": self.json_path,
            "primitive_type": self.data_type,
            "semantic_type": self.semantic_type,
            "description": self.description,
            "repeated": self.repeated,
            "statistics": self.statistics.to_dict_cdd(),
        }
        if self.array_length is not None:
            column["array_length"] = self.array_length
        return column


def _text_data_type(sample: list) -> str:
    """sc:Date or sc:DateTime for ISO-8601 strings, otherwise sc:Text.

    JSON strings stay text even when they look like numbers: the file said they
    are strings. Dates are the exception worth making, since search filters on them.
    """
    values = [v for v in sample if isinstance(v, str)]
    if len(values) >= 3:
        if all(_ISO_DATE.match(v) for v in values):
            return "sc:Date"
        if all(_ISO_DATE.match(v) or _ISO_DATETIME.match(v) for v in values):
            return "sc:DateTime"
    return "sc:Text"


def _top_values(acc: _PathAccumulator, family: Optional[str], non_null: int):
    """Most frequent values of a low-cardinality text or boolean field."""
    if family not in (TEXT, BOOLEAN) or acc.top_capped or not acc.top:
        return None
    if acc.is_long_text():
        # Long text goes to chunked_content for semantic search, not to facets.
        return None
    if len(acc.top) > TOP_VALUES_MAX_UNIQUE or len(acc.top) >= non_null:
        # Too many distinct values to facet on, or every value is unique (ids).
        return None
    return [{"value": value, "count": count} for value, count in acc.top.most_common(TOP_VALUES)]
