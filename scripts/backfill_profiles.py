#!/usr/bin/env python
"""Bring profiles already stored in MoMa up to date, without re-profiling them.

Adds what older profiles lack -- data quality, column statistics, semantic types
and document keywords -- onto the existing graph. No existing node id changes.
The plan and its reasoning are in 09-profile-backfill-handoff.md.

Runs inside the profiler Ray pod, which has the S3 mount, the LLM and database
credentials, and the profiler package this script reuses:

    kubectl -n athenarc cp scripts/backfill_profiles.py <pod>:/tmp/backfill_profiles.py
    python /tmp/backfill_profiles.py run --env dev --dataset <id>             # dry run
    python /tmp/backfill_profiles.py run --env dev --dataset <id> --write
    python /tmp/backfill_profiles.py rollback --env dev --ledger <file.jsonl>

A dry run does all the computing, including the LLM calls, and validates each
delta against MoMa, but never writes. Credentials come from the environment:
MOMA_USERNAME / MOMA_PASSWORD on dev, MOMA_TOKEN_URL / MOMA_CLIENT_ID /
MOMA_CLIENT_SECRET on prod.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
import traceback
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import requests

ENVIRONMENTS = {
    "dev": {
        "base_url": "https://datagems-dev.scayle.es/moma2/v1/api",
        "token_url": "https://datagems-dev.scayle.es/oauth/realms/dev/protocol/openid-connect/token",
    },
    "prod": {"base_url": "https://app.datagems.eu/moma2/v1/api", "token_url": None},
}

# Access tokens live 300 s and one dataset can take longer than that to compute,
# so a token is renewed before any call that would otherwise use a nearly dead one.
TOKEN_SAFETY_MARGIN_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 300
PAGE_SIZE = 100
NUMERIC_DATA_TYPES = ("sc:Integer", "sc:Float")
DB_HISTOGRAM_BINS = 10
DEFAULT_DB_STATEMENT_TIMEOUT_SECONDS = 120
# Full-table percentiles sort the column. ds_era5_land has tables of 240 to 735
# million rows, where every query would just run until the statement timeout.
DEFAULT_DB_MAX_ROWS = 10_000_000

BACKFILLS = ("A", "B", "C", "D")
WRITTEN, CLEAN = "written", "clean"
SKIPPED_LARGE, SKIPPED_EMPTY = "skipped_large", "skipped_empty"
SKIPPED_CHANGED, SKIPPED_MISSING = "skipped_changed", "skipped_missing"
UNREADABLE, FAILED = "unreadable", "failed"

NO_ERRORS_SUMMARY = "No data quality errors were detected."
DOCUMENT_SUFFIXES = (".pdf", ".txt")
# Older profiles put the set's label (PDFSet, TextSet) on the file object itself.
PDF_FILE_LABELS = {"PDF", "PDFSet"}
DOCUMENT_FILE_LABELS = PDF_FILE_LABELS | {"Text", "TextSet"}
DATA_QUALITY_LABELS = {
    "dg:DataQuality": ["DataQuality", "dg:DataQuality"],
    "dg:DataQualityError": ["DataQualityError", "dg:DataQualityError"],
}


class MomaError(Exception):
    """A MoMa call failed."""


class DatasetUnreadable(MomaError):
    """GET /datasets/{id} answered 500: the stored graph cannot be decoded."""


class TableTooLarge(MomaError):
    """A source table is too big to compute full-table statistics on."""


class StopRun(Exception):
    """A condition that must end the whole run, not just one dataset."""


# -- MoMa access -------------------------------------------------------------------------


class TokenSource:
    """Fetches access tokens on demand, renewing them shortly before they expire."""

    def __init__(self, token_url: str, form: dict, session: requests.Session):
        self._token_url = token_url
        self._form = form
        self._session = session
        self._token: Optional[str] = None
        self._expires_at = 0.0

    @classmethod
    def from_environment(cls, env: str, session: requests.Session) -> "TokenSource":
        if env == "dev":
            return cls(
                ENVIRONMENTS["dev"]["token_url"],
                {
                    "grant_type": "password",
                    "client_id": "swagger-client",
                    "scope": "datagems",
                    "username": os.environ.get("MOMA_USERNAME", "dg-user-admin"),
                    "password": _required_env("MOMA_PASSWORD"),
                },
                session,
            )
        return cls(
            _required_env("MOMA_TOKEN_URL"),
            {
                "grant_type": "client_credentials",
                "client_id": _required_env("MOMA_CLIENT_ID"),
                "client_secret": _required_env("MOMA_CLIENT_SECRET"),
            },
            session,
        )

    def get(self) -> str:
        if self._token is None or time.time() >= self._expires_at - TOKEN_SAFETY_MARGIN_SECONDS:
            response = self._session.post(self._token_url, data=self._form, timeout=30)
            if response.status_code != 200:
                # The body can echo the request, so only the status is reported.
                raise MomaError(f"token request failed with HTTP {response.status_code}")
            body = response.json()
            self._token = body["access_token"]
            self._expires_at = time.time() + float(body.get("expires_in", 300))
        return self._token


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set {name} in the environment.")
    return value


class MomaClient:
    def __init__(self, base_url: str, tokens: TokenSource, session: requests.Session):
        self._base_url = base_url.rstrip("/")
        self._tokens = tokens
        self._session = session

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        return self._session.request(
            method,
            f"{self._base_url}{path}",
            headers={"Authorization": f"Bearer {self._tokens.get()}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            **kwargs,
        )

    def _json(self, method: str, path: str, **kwargs) -> Any:
        response = self._request(method, path, **kwargs)
        if response.status_code != 200:
            raise MomaError(f"{method} {path}: HTTP {response.status_code}: {response.text[:500]}")
        return response.json()

    def ready_dataset_ids(self) -> list[str]:
        ids: list[str] = []
        page = 1
        while True:
            body = self._json(
                "GET",
                "/datasets/",
                params={"status": "ready", "pageSize": PAGE_SIZE, "page": page, "properties": "id"},
            )
            batch = _dataset_ids_of_listing(body)
            ids.extend(i for i in batch if i not in ids)
            if len(batch) < PAGE_SIZE:
                return ids
            page += 1

    def dataset(self, dataset_id: str) -> dict:
        response = self._request("GET", f"/datasets/{dataset_id}")
        if response.status_code == 500:
            raise DatasetUnreadable(f"GET /datasets/{dataset_id}: HTTP 500")
        if response.status_code != 200:
            raise MomaError(f"GET /datasets/{dataset_id}: HTTP {response.status_code}")
        return response.json()

    def convert(self, croissant: dict) -> dict:
        return self._json("POST", "/datasets/convert", json=croissant)

    def validate(self, delta: dict) -> dict:
        return self._json("POST", "/datasets/validate", json=delta)

    def write(self, delta: dict) -> None:
        """Write a delta. A 200 proves nothing: MoMa also answers 200 on a failed write."""
        self._json("POST", "/datasets/", json=delta)

    def patch_node(self, node_id: str, properties: dict) -> None:
        self._json("PATCH", f"/nodes/{node_id}", json=properties)


def _dataset_ids_of_listing(body: Any) -> list[str]:
    """Dataset ids in a listing, which is an object of datasets holding PG-JSON graphs."""
    datasets = body.get("datasets", []) if isinstance(body, dict) else body
    ids = []
    for dataset in datasets:
        if "nodes" in dataset:
            ids.extend(n["id"] for n in dataset["nodes"] if "sc:Dataset" in n.get("labels", []))
        else:
            ids.append(dataset["id"])
    return ids


# -- The stored graph --------------------------------------------------------------------


class Graph:
    """One dataset's PG-JSON subgraph, as returned by GET /datasets/{id}."""

    def __init__(self, payload: dict):
        self.nodes: dict[str, dict] = {n["id"]: n for n in payload["nodes"]}
        self._out: dict[tuple[str, str], list[str]] = defaultdict(list)
        for edge in payload.get("edges") or []:
            for label in edge["labels"]:
                self._out[(edge["from"], label)].append(edge["to"])
        roots = [n for n in self.nodes.values() if "sc:Dataset" in n["labels"]]
        if len(roots) != 1:
            raise MomaError(f"expected one sc:Dataset root, found {len(roots)}")
        self.root_id: str = roots[0]["id"]

    def children(self, node_id: str, label: str) -> list[dict]:
        return [self.nodes[i] for i in self._out[(node_id, label)] if i in self.nodes]

    def has_edge(self, source: str, target: str, label: str) -> bool:
        return target in self._out[(source, label)]

    def record_sets(self) -> list[dict]:
        return self.children(self.root_id, "recordSet")

    def with_label(self, label: str) -> list[dict]:
        return [n for n in self.nodes.values() if label in n["labels"]]


def is_blank(value: Any) -> bool:
    """Whether a stored property counts as missing: absent, "", [] or null."""
    return value is None or value == "" or value == []


def statistics_is_empty(node: dict) -> bool:
    return set(node.get("properties", {})) <= {"type"}


def normalize_content_url(url: str) -> str:
    """A FileObject contentUrl as a path on the pod's S3 mount."""
    return "/s3/" + url[len("s3://") :] if url.startswith("s3://") else url


def parse_content_size(value: Any) -> Optional[int]:
    """Bytes in a contentSize such as "2010494 B", or None if it is not in that form."""
    match = re.fullmatch(r"\s*(\d+)\s*B\s*", str(value))
    return int(match.group(1)) if match else None


def document_stem(name: str) -> str:
    """The comparable name of a document, given a record set or file object name.

    Older record sets are named "138.pdf" or a full /s3/dataset/... path. Only the
    known document suffixes are removed, because a stem can itself contain dots.
    """
    base = name.rstrip("/").rsplit("/", 1)[-1]
    for suffix in DOCUMENT_SUFFIXES:
        if base.lower().endswith(suffix):
            return base[: -len(suffix)]
    return base


@dataclass
class TableSource:
    kind: str  # csv, excel, db or json
    record_set: dict
    file_object: dict
    columns: list[dict]


def resolve_table(graph: Graph, record_set: dict) -> tuple[Optional[TableSource], str]:
    """Where a tabular record set's data lives, with a reason when it cannot be told."""
    columns = [c for c in graph.children(record_set["id"], "field") if "Column" in c["labels"]]
    if not columns:
        return None, "no_columns"
    file_objects = {
        f["id"]: f for column in columns for f in graph.children(column["id"], "source/fileObject")
    }
    if len(file_objects) != 1:
        return None, f"columns_point_to_{len(file_objects)}_file_objects"
    file_object = next(iter(file_objects.values()))
    for label, kind in (("CSV", "csv"), ("EXCEL", "excel"), ("Table", "db"), ("JSON", "json")):
        if label in file_object["labels"]:
            return TableSource(kind, record_set, file_object, columns), ""
    return None, f"unsupported_file_object_{sorted(file_object['labels'])}"


def match_document_file(graph: Graph, record_set: dict) -> tuple[Optional[dict], str]:
    """The PDF or text FileObject a document record set describes, matched by name."""
    stem = document_stem(str(record_set.get("properties", {}).get("name", "")))
    if not stem:
        return None, "record_set_has_no_name"
    matches = [
        node
        for node in graph.nodes.values()
        if "cr:FileObject" in node["labels"]
        and set(node["labels"]) & DOCUMENT_FILE_LABELS
        and stem in _file_object_stems(node)
    ]
    if len(matches) > 1:
        return None, "ambiguous_name"
    if not matches:
        return None, "no_file_object_with_that_name"
    return matches[0], ""


def _file_object_stems(node: dict) -> set[str]:
    properties = node.get("properties", {})
    return {
        document_stem(str(value))
        for value in (properties.get("name"), properties.get("contentUrl"))
        if value
    }


# -- The delta sent to MoMa --------------------------------------------------------------


class Delta:
    """Every change for one dataset, sent as a single write so it applies all or nothing."""

    def __init__(self, graph: Graph, run_properties: dict):
        self.graph = graph
        self.run_properties = run_properties
        self.nodes: dict[str, dict] = {}
        self.edges: dict[tuple[str, str, str], dict] = {}

    @property
    def is_empty(self) -> bool:
        return not self.nodes

    def _touch(self, node_id: str) -> dict:
        """Reference an existing node with exactly its stored labels.

        MERGE matches on (labels, id), so any other label set would create a
        second node with the same id instead of updating this one.
        """
        if node_id not in self.nodes:
            stored = self.graph.nodes[node_id]
            properties = {}
            if node_id == self.graph.root_id:
                properties["type"] = "sc:Dataset"
            self.nodes[node_id] = {"id": node_id, "labels": list(stored["labels"]), "properties": properties}
        return self.nodes[node_id]

    def link(self, source: str, target: str, label: str) -> None:
        self._touch(source)
        self._touch(target)
        self.edges[(source, target, label)] = {"from": source, "to": target, "labels": [label], "properties": {}}

    def link_record_set(self, record_set_id: str) -> None:
        self.link(self.graph.root_id, record_set_id, "recordSet")

    def link_column(self, record_set_id: str, column_id: str) -> None:
        self.link_record_set(record_set_id)
        self.link(record_set_id, column_id, "field")

    def set_properties(self, node_id: str, properties: dict) -> None:
        self._touch(node_id)["properties"].update(properties)

    def add_converted(self, converted: dict) -> list[str]:
        """Merge a /datasets/convert result in, returning the ids of its new nodes."""
        new_ids = []
        for node in converted["nodes"]:
            node_id = node["id"]
            if node_id in self.graph.nodes:
                self._touch(node_id)
                continue
            properties = {k: v for k, v in node.get("properties", {}).items() if not is_blank(v)}
            if "DataQuality" in node["labels"]:
                properties.update(self.run_properties)
            self.nodes[node_id] = {"id": node_id, "labels": list(node["labels"]), "properties": properties}
            new_ids.append(node_id)
        for edge in converted.get("edges") or []:
            for label in edge["labels"]:
                self.edges[(edge["from"], edge["to"], label)] = {
                    "from": edge["from"],
                    "to": edge["to"],
                    "labels": [label],
                    "properties": {},
                }
        return new_ids

    def payload(self) -> dict:
        return {"nodes": list(self.nodes.values()), "edges": list(self.edges.values())}


def check_delta(delta: Delta) -> None:
    """Refuse a delta that breaks the write rules, before MoMa ever sees it."""
    payload = delta.payload()
    json.dumps(payload, allow_nan=False)  # raises on NaN/Infinity, which MoMa cannot read back
    for node in payload["nodes"]:
        stored = delta.graph.nodes.get(node["id"])
        if stored is not None and sorted(stored["labels"]) != sorted(node["labels"]):
            raise MomaError(f"labels differ from the stored node {node['id']}")
        if stored is None and sorted(node["labels"]) not in [sorted(v) for v in DATA_QUALITY_LABELS.values()]:
            raise MomaError(f"unexpected new node {node['id']} with labels {node['labels']}")
    known = set(delta.nodes)
    for source, target, _ in delta.edges:
        if source not in known or target not in known:
            raise MomaError(f"edge {source} -> {target} leaves the delta")


def verify_written(delta: Delta, after: Graph) -> list[str]:
    """What is wrong with the stored graph after a write; empty when it all landed."""
    problems = []
    for node in delta.nodes.values():
        stored = after.nodes.get(node["id"])
        if stored is None:
            problems.append(f"node {node['id']} is missing")
            continue
        if sorted(stored["labels"]) != sorted(node["labels"]):
            problems.append(f"node {node['id']} has labels {stored['labels']}")
        for key, expected in node["properties"].items():
            if not _same_value(stored.get("properties", {}).get(key), expected):
                problems.append(f"node {node['id']} property {key} did not land")
    for source, target, label in delta.edges:
        if not after.has_edge(source, target, label):
            problems.append(f"edge {source} -{label}-> {target} is missing")
    return problems


def _same_value(actual: Any, expected: Any) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12)
    return actual == expected


def statistics_properties(statistics: dict) -> dict:
    """Profiler statistics as properties for an existing node.

    Keeps the node's own id and type. Drops nulls, which would be no-ops, and
    NaN/Infinity (a one-row column has a NaN variance), which MoMa stores but then
    cannot return as JSON, making the whole dataset unreadable.
    """
    return {
        key: value
        for key, value in statistics.items()
        if key not in ("@id", "@type")
        and value is not None
        and not (isinstance(value, float) and not math.isfinite(value))
    }


def quote_identifier(name: str) -> str:
    """A SQL identifier, safe for mixed case and for SQLAlchemy's text() bind syntax."""
    return '"' + name.replace('"', '""').replace(":", "\\:") + '"'


def _single_row(result: Any) -> Any:
    return _frame(result).iloc[0]


def _frame(result: Any) -> Any:
    # DatagemsPostgres.execute reports a failed query as {"error": ...}.
    if isinstance(result, dict):
        raise MomaError(f"query failed: {result.get('error')}")
    return result


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    number = float(value)
    return None if math.isnan(number) else number


def check_table_size(execute: Any, table: str, max_rows: int) -> None:
    """Raise TableTooLarge from the planner's row estimate, which costs nothing to read.

    A table that was never analysed has no estimate (-1, or 0 for a parent table)
    and goes ahead, bounded by the statement timeout.
    """
    literal = quote_identifier(table).replace("'", "''")
    rows = _frame(execute(f"SELECT CAST(reltuples AS bigint) AS estimate FROM pg_class WHERE oid = to_regclass('{literal}')"))
    if len(rows) and int(rows.iloc[0]["estimate"]) > max_rows:
        raise TableTooLarge(f"about {int(rows.iloc[0]['estimate'])} rows, limit {max_rows}")


def compute_db_statistics(execute: Any, table: str, column: str, data_type: str, statistics_class: Any) -> dict:
    """Statistics of one database column, in the same shape and meaning as a CSV column.

    Replaces calculate_statistics_of_db, which is disabled in the profiler and
    reports a missing count of 0 for every numeric column, computes numeric values
    from the first 1000 rows only, and cannot read mixed-case names.
    """
    quoted_table, quoted_column = quote_identifier(table), quote_identifier(column)

    if data_type not in NUMERIC_DATA_TYPES:
        row = _single_row(execute(
            f"SELECT COUNT(*) AS total, COUNT({quoted_column}) AS present, "
            f"COUNT(DISTINCT CAST({quoted_column} AS text)) AS unique_values FROM {quoted_table}"
        ))
        total, present = int(row["total"]), int(row["present"])
        if total == 0:
            return statistics_class().to_dict()
        return statistics_class(
            row_count=present,
            missing_count=total - present,
            missing_percentage=(total - present) / total * 100,
            unique_count=int(row["unique_values"]),
        ).to_dict()

    value = f"CAST({quoted_column} AS double precision)"
    row = _single_row(execute(
        f"SELECT COUNT(*) AS total, COUNT({quoted_column}) AS present, AVG({value}) AS mean_value, "
        f"STDDEV_SAMP({value}) AS std_value, VAR_SAMP({value}) AS variance_value, "
        f"MIN({value}) AS low, MAX({value}) AS high, "
        f"PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY {value}) AS p05, "
        f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {value}) AS p50, "
        f"PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {value}) AS p95 "
        f"FROM {quoted_table}"
    ))
    total, present = int(row["total"]), int(row["present"])
    if total == 0:
        return statistics_class().to_dict()
    missing = total - present
    missing_percentage = missing / total * 100
    if present == 0:
        return statistics_class(
            row_count=0, missing_count=missing, missing_percentage=missing_percentage, histogram=[], unique_count=0
        ).to_dict()

    low, high = float(row["low"]), float(row["high"])
    return statistics_class(
        row_count=present,
        mean=_number(row["mean_value"]),
        median=_number(row["p50"]),
        standard_deviation=_number(row["std_value"]),
        min_value=low,
        max_value=high,
        missing_count=missing,
        missing_percentage=missing_percentage,
        histogram=_db_histogram(execute, quoted_table, quoted_column, value, low, high, present),
        variance=_number(row["variance_value"]),
        range_value=high - low,
        percentile05=_number(row["p05"]),
        percentile95=_number(row["p95"]),
        generated_at=datetime.now(timezone.utc).isoformat(),
    ).to_dict()


def _db_histogram(execute, quoted_table, quoted_column, value, low, high, present) -> list[dict]:
    """Ten equal-width bins, including empty ones, like the histogram of a CSV column."""
    counts = [0] * DB_HISTOGRAM_BINS
    if low == high:
        # width_bucket rejects equal bounds. A CSV column widens the range the same way.
        margin = 0.001 * abs(low) if low != 0 else 0.001
        start, width = low - margin, 2 * margin / DB_HISTOGRAM_BINS
        counts[DB_HISTOGRAM_BINS // 2 - 1] = present
    else:
        start, width = low, (high - low) / DB_HISTOGRAM_BINS
        # width_bucket puts the maximum one past the last bin, so it is folded back in.
        rows = _frame(execute(
            f"SELECT LEAST(width_bucket({value}, CAST({low!r} AS double precision), "
            f"CAST({high!r} AS double precision), {DB_HISTOGRAM_BINS}), {DB_HISTOGRAM_BINS}) AS bucket, "
            f"COUNT(*) AS rows_in_bucket FROM {quoted_table} WHERE {quoted_column} IS NOT NULL GROUP BY 1"
        ))
        for _, row in rows.iterrows():
            counts[int(row["bucket"]) - 1] = int(row["rows_in_bucket"])
    return [
        {"binRange": [start + i * width, start + (i + 1) * width], "count": counts[i]}
        for i in range(DB_HISTOGRAM_BINS)
    ]


def usable_semantic_type(value: Any) -> bool:
    """A real annotation: not "", not None and not the annotator's failure marker."""
    return isinstance(value, str) and bool(value.strip()) and value != "error"


# -- The profiler functions --------------------------------------------------------------


def pdf_text_reader(pdf_module: Any) -> Any:
    """The function returning a PDF's full text, whichever way this image names it.

    Images up to v0.0.35 have parse_and_chunk_pdf, returning (text, chunks); later
    code has parse_pdf, returning the text alone.
    """
    if hasattr(pdf_module, "parse_pdf"):
        return pdf_module.parse_pdf
    if hasattr(pdf_module, "parse_and_chunk_pdf"):
        return lambda path: pdf_module.parse_and_chunk_pdf(path)[0]
    raise SystemExit("This profiler image has no function that extracts PDF text.")


class ProfilerEngine:
    """The profiler's own code, imported lazily so results match a fresh profile."""

    def __init__(
        self,
        db_statement_timeout_seconds: int = DEFAULT_DB_STATEMENT_TIMEOUT_SECONDS,
        db_max_rows: int = DEFAULT_DB_MAX_ROWS,
    ):
        # Imported here because the profiler pulls in torch and docling at import
        # time, and a missing function in an older image must fail before any work.
        from sqlalchemy import create_engine

        from dataset_profiler.data_quality.detector import MAX_FILE_SIZE_MB, detect_data_quality_errors
        from dataset_profiler.profile_components.generic_types.table import ColumnStatistics
        from dataset_profiler.profile_components.cta import ColumnTypeAnnotator
        from dataset_profiler.profile_components.record_set.csv import csv_record_set
        from dataset_profiler.profile_components.record_set.csv.calculate_statistics import _ColumnAccumulator
        from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres
        from dataset_profiler.profile_components.record_set.document_description import (
            MIN_INPUT_WORDS,
            describe_document,
            is_document_llm_enabled,
        )
        from dataset_profiler.profile_components.record_set.json.json_record_set import JSONRecordSet
        from dataset_profiler.profile_components.record_set.pdf import pdf_record_set
        from dataset_profiler.profile_components.record_set.text.text_utilities import (
            read_file_with_encoding,
            text_preprocess,
        )
        import pandas as pd

        if not is_document_llm_enabled():
            raise SystemExit("ENABLE_DOCUMENT_LLM is off, so document keywords would all come back empty.")

        self._pd = pd
        self._detect = detect_data_quality_errors
        self.max_data_quality_file_mb = MAX_FILE_SIZE_MB
        self._annotator = ColumnTypeAnnotator
        self._csv = csv_record_set
        self._accumulator = _ColumnAccumulator
        self._postgres = DatagemsPostgres
        self._create_engine = create_engine
        self._statistics_class = ColumnStatistics
        self._db_statement_timeout_ms = db_statement_timeout_seconds * 1000
        self._describe = describe_document
        self.min_document_words = MIN_INPUT_WORDS
        self._json_record_set = JSONRecordSet
        self._parse_pdf = pdf_text_reader(pdf_record_set)
        self._read_text = read_file_with_encoding
        self._text_preprocess = text_preprocess
        self._connections: dict[tuple[str, str], Any] = {}
        self._db_statistics_cache: dict[tuple[str, str, str, str], Any] = {}
        self._db_max_rows = db_max_rows

    def excel_sheet_to_csv(self, workbook: str, sheet: str, directory: str) -> Optional[str]:
        """The sheet as a CSV, like the Excel path of a fresh profile; None when empty."""
        with self._pd.ExcelFile(workbook) as xls:
            frame = self._pd.read_excel(xls, sheet_name=sheet)
        if frame.empty:
            return None
        path = os.path.join(directory, f"{uuid.uuid4()}.csv")
        frame.to_csv(path, index=False, sep=",")
        return path

    def open_csv(self, path: str) -> Any:
        """A CSVRecordSet that only resolves this file's encoding and delimiter."""
        record_set = self._csv.CSVRecordSet.__new__(self._csv.CSVRecordSet)
        record_set.distribution_path = os.path.dirname(path)
        record_set.file_object = os.path.basename(path)
        record_set._encoding = None
        record_set.backfill_path = path
        record_set.backfill_delimiter = record_set._detect_delimiter(path)
        return record_set

    def data_quality(self, table: Any, table_name: str) -> Any:
        return self._detect(
            table.backfill_path,
            table_name=Path(table_name).name,
            delimiter=table.backfill_delimiter,
            encoding=table.encoding,
        )

    def csv_statistics(self, table: Any) -> dict[str, dict]:
        """Per-column statistics, in the same two passes as CSVRecordSet.extract_fields."""
        path, delimiter = table.backfill_path, table.backfill_delimiter
        names = table._read_column_names(path, delimiter)
        accumulators = {name: self._accumulator() for name in names}
        for chunk in table._iter_chunks(path, delimiter):
            for name in names:
                if name in chunk.columns:
                    accumulators[name].update(chunk[name])
        numeric = [name for name, accumulator in accumulators.items() if accumulator.needs_histogram()]
        if numeric:
            for chunk in table._iter_chunks(path, delimiter, usecols=numeric):
                for name in numeric:
                    if name in chunk.columns:
                        accumulators[name].update_histogram(chunk[name])
        return {name: accumulator.build_statistics().to_dict() for name, accumulator in accumulators.items()}

    def csv_semantic_types(self, table: Any, columns: list[str]) -> dict[str, Optional[str]]:
        sample = self._pd.read_csv(
            table.backfill_path,
            encoding=table.encoding,
            sep=table.backfill_delimiter,
            nrows=self._csv.CTA_SAMPLE_ROWS,
            on_bad_lines="skip",
        )
        return self._annotator().annotate_columns(df=sample, columns_to_annotate=columns)

    def json_semantic_types(self, path: str, file_object_id: str) -> dict[str, Optional[str]]:
        return self._json_record_set(path, file_object_id, use_llm=False)._annotate_semantic_types()

    def connection(self, database: str, engine: str) -> Any:
        key = (database, engine)
        if key not in self._connections:
            connector = self._postgres(database, "public", engine)
            # The backfill only reads source databases, and must not be able to
            # occupy one with a query on a very large table.
            connector.engine = self._create_engine(
                connector.connection_uri,
                connect_args={
                    "options": (
                        "-c search_path=public "
                        f"-c statement_timeout={self._db_statement_timeout_ms} "
                        "-c default_transaction_read_only=on"
                    )
                },
            )
            self._connections[key] = connector
        return self._connections[key]

    def db_semantic_types(self, connection: Any, table: str, columns: list[str]) -> dict[str, Optional[str]]:
        return self._annotator().annotate_columns(
            db=connection, table_name=quote_identifier(table), columns_to_annotate=columns
        )

    def db_statistics(self, connection: Any, table: str, column: str, data_type: str) -> dict:
        # Dev has the same few databases profiled into many datasets, each with
        # its own Statistics nodes, so one computation serves them all. Failures
        # are kept too: repeating a query that timed out only repeats the load.
        key = (connection.connection_uri, table, column, data_type)
        if key not in self._db_statistics_cache:
            try:
                check_table_size(connection.execute, table, self._db_max_rows)
                self._db_statistics_cache[key] = compute_db_statistics(
                    connection.execute, table, column, data_type, self._statistics_class
                )
            except MomaError as e:
                self._db_statistics_cache[key] = e
        cached = self._db_statistics_cache[key]
        if isinstance(cached, Exception):
            raise cached
        return cached

    def document_text(self, path: str, is_pdf: bool) -> str:
        if is_pdf:
            return self._parse_pdf(path)
        text, _ = self._read_text(path)
        _, body = self._text_preprocess(text, separator=None, header_index=0, main_text_index=1)
        return body

    def describe(self, text: str, name: str) -> Any:
        return self._describe(text, name=name)


def database_engine(connection_node: dict) -> str:
    """Which configured server a dg:DatabaseConnection points at.

    The profile stores only contentUrl (protocol://host:port/database), not the
    engine name. The port decides, because the host in a stored URL is whichever
    cluster node served the profile and need not be the host configured here.
    """
    url = str(connection_node.get("properties", {}).get("contentUrl", ""))
    match = re.match(r"[^:]+://[^:/]+:(\d+)", url)
    port = match.group(1) if match else ""
    if port and port == os.environ.get("DATAGEMS_TIMESCALE_DB_PORT"):
        return "TimescaleDB"
    if port and port == os.environ.get("DATAGEMS_POSTGRES_PORT"):
        return "PostgreSQL"
    raise MomaError(f"no configured database server has port {port!r}")


# -- The ledger --------------------------------------------------------------------------


class Ledger:
    """One JSON line per target, flushed as it is written so a crash loses nothing."""

    def __init__(self, path: Path, run_id: str, env: str, applied: bool):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file = path.open("a", encoding="utf-8")
        self._common = {"run_id": run_id, "env": env}
        self._applied = applied
        self.counts: Counter = Counter()

    def record(self, entry: dict) -> None:
        line = {**self._common, "applied": entry.get("outcome") in (WRITTEN, CLEAN) and self._applied, **entry}
        self._file.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
        self.counts[(entry.get("backfill"), entry["outcome"])] += 1

    def close(self) -> None:
        self._file.close()


@dataclass
class Options:
    backfills: set[str] = field(default_factory=lambda: set(BACKFILLS))
    write: bool = False
    stop_on_unreadable: bool = False
    deltas_dir: Optional[Path] = None


# -- Backfilling one dataset -------------------------------------------------------------


class Backfiller:
    def __init__(self, moma: Any, engine: Any, ledger: Ledger, options: Options, run_id: str, version: str):
        self.moma = moma
        self.engine = engine
        self.ledger = ledger
        self.options = options
        self.run_properties = {
            "backfillRunId": run_id,
            "backfilledAt": datetime.now(timezone.utc).isoformat(),
            "profilerVersion": version,
        }

    def process(self, dataset_id: str) -> None:
        started = time.monotonic()
        try:
            graph = Graph(self.moma.dataset(dataset_id))
        except DatasetUnreadable as e:
            self.ledger.record(self._entry(dataset_id, dataset_id, "Dataset", None, UNREADABLE, started, detail=str(e)))
            if self.options.stop_on_unreadable:
                raise StopRun(f"{e}. Stopping as required before any production write.") from e
            return
        delta = Delta(graph, self.run_properties)
        entries: list[dict] = []
        with tempfile.TemporaryDirectory(prefix="backfill-") as workdir:
            for record_set in graph.record_sets():
                self._process_record_set(dataset_id, graph, record_set, delta, entries, workdir)
        self._apply(dataset_id, delta, entries)

    def _process_record_set(self, dataset_id, graph, record_set, delta, entries, workdir) -> None:
        table, reason = resolve_table(graph, record_set)
        if table is not None:
            self._process_table(dataset_id, graph, table, delta, entries, workdir)
            return
        if reason == "no_columns" and self._wants_document(graph, record_set):
            self._process_document(dataset_id, graph, record_set, delta, entries)
        elif reason != "no_columns":
            self._report_unresolved_table(dataset_id, graph, record_set, reason, entries)

    def _report_unresolved_table(self, dataset_id, graph, record_set, reason, entries) -> None:
        for column in graph.children(record_set["id"], "field"):
            if "C" in self.options.backfills and is_blank(column.get("properties", {}).get("semanticType")):
                entries.append(
                    self._entry(dataset_id, column["id"], "Column", "C", SKIPPED_MISSING, time.monotonic(), detail=reason)
                )

    def _entry(self, dataset_id, node_id, kind, backfill, outcome, started, **extra) -> dict:
        return {
            "dataset_id": dataset_id,
            "node_id": node_id,
            "node_kind": kind,
            "backfill": backfill,
            "outcome": outcome,
            "new_node_ids": extra.pop("new_node_ids", []),
            "properties": extra.pop("properties", {}),
            "previous": extra.pop("previous", {}),
            "duration_s": round(time.monotonic() - started, 3),
            **extra,
        }

    # -- tabular record sets ----------------------------------------------------------

    def _process_table(self, dataset_id, graph, table, delta, entries, workdir) -> None:
        wants_quality = (
            "A" in self.options.backfills
            and table.kind in ("csv", "excel")
            and not graph.children(table.record_set["id"], "HAS_DATA_QUALITY")
        )
        statistics_targets = self._statistics_targets(graph, table)
        semantic_targets = self._semantic_targets(table)
        if not (wants_quality or statistics_targets or semantic_targets):
            return

        targets = (
            ([(table.record_set["id"], "RecordSet", "A")] if wants_quality else [])
            + [(stats["id"], "Statistics", "B") for _, stats in statistics_targets]
            + [(column["id"], "Column", "C") for column in semantic_targets]
        )

        def skip_all(outcome: str, detail: str) -> None:
            entries.extend(
                self._entry(dataset_id, node, kind, letter, outcome, time.monotonic(), detail=detail)
                for node, kind, letter in targets
            )

        if table.kind == "db":
            try:
                connection = self._db_connection(graph, table)
            except Exception as e:  # noqa: BLE001 - one bad connection must not stop the dataset
                skip_all(FAILED, f"db_connection: {e}")
                return
            self._table_statistics_db(dataset_id, table, connection, statistics_targets, delta, entries)
            self._table_semantic_db(dataset_id, table, connection, semantic_targets, delta, entries)
            return

        path = normalize_content_url(str(table.file_object.get("properties", {}).get("contentUrl", "")))
        problem = self._file_problem(path, table.file_object)
        if problem:
            skip_all(*problem)
            return

        if table.kind == "json":
            self._table_semantic_json(dataset_id, table, path, semantic_targets, delta, entries)
            return

        try:
            handle = self._open_table(table, path, workdir)
        except Exception as e:  # noqa: BLE001 - logged in the ledger, other tables continue
            skip_all(FAILED, f"open: {e}")
            return
        if handle is None:
            skip_all(SKIPPED_EMPTY, "empty_sheet")
            return

        if wants_quality:
            self._table_quality(dataset_id, table, handle, delta, entries)
        self._table_statistics_file(dataset_id, table, handle, statistics_targets, delta, entries)
        self._table_semantic_file(dataset_id, table, handle, semantic_targets, delta, entries)

    def _statistics_targets(self, graph, table) -> list[tuple[dict, dict]]:
        if "B" not in self.options.backfills or table.kind == "json":
            return []
        return [
            (column, statistics)
            for column in table.columns
            for statistics in graph.children(column["id"], "statistics")
            if statistics_is_empty(statistics)
        ]

    def _semantic_targets(self, table) -> list[dict]:
        if "C" not in self.options.backfills:
            return []
        return [c for c in table.columns if is_blank(c.get("properties", {}).get("semanticType"))]

    @staticmethod
    def _file_problem(path: str, file_object: dict) -> Optional[tuple[str, str]]:
        """Why this file cannot be trusted to be the one that was profiled, if so."""
        if not path or not os.path.isfile(path):
            return SKIPPED_MISSING, f"file_not_found: {path}"
        expected = parse_content_size(file_object.get("properties", {}).get("contentSize"))
        if expected is None:
            return SKIPPED_CHANGED, "content_size_unknown"
        actual = os.path.getsize(path)
        if actual != expected:
            return SKIPPED_CHANGED, f"size_{actual}_expected_{expected}"
        return None

    def _open_table(self, table, path, workdir) -> Any:
        if table.kind == "excel":
            sheet = str(table.record_set.get("properties", {}).get("name", ""))
            path = self.engine.excel_sheet_to_csv(path, sheet, workdir)
            if path is None:
                return None
        return self.engine.open_csv(path)

    @staticmethod
    def _column_key(column: dict) -> str:
        properties = column.get("properties", {})
        return properties.get("column") or properties.get("name") or ""

    def _table_quality(self, dataset_id, table, handle, delta, entries) -> None:
        started = time.monotonic()
        record_set_id = table.record_set["id"]

        def done(outcome: str, **extra) -> None:
            entries.append(self._entry(dataset_id, record_set_id, "RecordSet", "A", outcome, started, **extra))

        size_mb = os.path.getsize(handle.backfill_path) / (1024 * 1024)
        if size_mb > self.engine.max_data_quality_file_mb:
            done(SKIPPED_LARGE, detail=f"{size_mb:.1f} MB")
            return
        name = str(table.record_set.get("properties", {}).get("name", ""))
        try:
            result = self.engine.data_quality(handle, name)
        except Exception as e:  # noqa: BLE001 - retried by a later run
            done(FAILED, detail=f"{type(e).__name__}: {e}"[:800])
            return
        if result is None:  # the size was checked above, so only an empty table remains
            done(SKIPPED_EMPTY)
            return

        block = result.to_dict()
        clean = not block["errors"]
        if clean:
            block["summary"] = NO_ERRORS_SUMMARY
        try:
            converted = self.moma.convert(
                {
                    "@context": {},
                    "@type": "sc:Dataset",
                    "@id": dataset_id,
                    "recordSet": [{"@type": "cr:RecordSet", "@id": record_set_id, "dataQuality": block}],
                }
            )
            new_ids = delta.add_converted(converted)
        except Exception as e:  # noqa: BLE001 - nothing was added to the delta
            done(FAILED, detail=f"convert: {e}"[:800])
            return
        done(CLEAN if clean else WRITTEN, new_node_ids=new_ids, error_count=len(block["errors"]))

    def _table_statistics_file(self, dataset_id, table, handle, targets, delta, entries) -> None:
        if not targets:
            return
        started = time.monotonic()
        try:
            computed = self.engine.csv_statistics(handle)
        except Exception as e:  # noqa: BLE001 - retried by a later run
            entries.extend(
                self._entry(dataset_id, s["id"], "Statistics", "B", FAILED, started, detail=f"{type(e).__name__}: {e}"[:800])
                for _, s in targets
            )
            return
        for column, statistics in targets:
            key = self._column_key(column)
            self._store_statistics(dataset_id, table, column, statistics, computed.get(key), delta, entries, started)

    def _store_statistics(self, dataset_id, table, column, statistics, computed, delta, entries, started) -> None:
        if computed is None:
            entries.append(self._entry(dataset_id, statistics["id"], "Statistics", "B", SKIPPED_MISSING, started, detail="column_not_in_source"))
            return
        properties = statistics_properties(computed)
        if not properties:
            entries.append(self._entry(dataset_id, statistics["id"], "Statistics", "B", SKIPPED_EMPTY, started))
            return
        delta.link_column(table.record_set["id"], column["id"])
        delta.link(column["id"], statistics["id"], "statistics")
        delta.set_properties(statistics["id"], properties)
        entries.append(self._entry(dataset_id, statistics["id"], "Statistics", "B", WRITTEN, started, properties=properties))

    def _table_semantic_file(self, dataset_id, table, handle, targets, delta, entries) -> None:
        if not targets:
            return
        started = time.monotonic()
        names = [self._column_key(c) for c in targets]
        try:
            annotations = self.engine.csv_semantic_types(handle, names)
        except Exception as e:  # noqa: BLE001 - retried by a later run
            annotations = None
            detail = f"{type(e).__name__}: {e}"[:800]
        else:
            detail = ""
        self._store_semantic(dataset_id, table, targets, annotations, detail, self._column_key, delta, entries, started)

    def _table_semantic_json(self, dataset_id, table, path, targets, delta, entries) -> None:
        if not targets:
            return
        started = time.monotonic()
        detail = ""
        try:
            annotations = self.engine.json_semantic_types(path, table.file_object["id"])
        except Exception as e:  # noqa: BLE001 - retried by a later run
            annotations, detail = None, f"{type(e).__name__}: {e}"[:800]
        self._store_semantic(
            dataset_id, table, targets, annotations, detail,
            lambda c: c.get("properties", {}).get("name", ""), delta, entries, started,
        )

    def _db_connection(self, graph, table) -> Any:
        parents = graph.children(table.file_object["id"], "containedIn")
        connections = [p for p in parents if "dg:DatabaseConnection" in p["labels"]]
        if len(connections) != 1:
            raise MomaError(f"table has {len(connections)} database connections")
        node = connections[0]
        return self.engine.connection(str(node["properties"]["name"]), database_engine(node))

    @staticmethod
    def _table_name(table) -> str:
        properties = table.file_object.get("properties", {})
        return str(properties.get("name") or table.record_set.get("properties", {}).get("name", ""))

    def _table_statistics_db(self, dataset_id, table, connection, targets, delta, entries) -> None:
        name = self._table_name(table)
        for column, statistics in targets:
            started = time.monotonic()
            try:
                computed = self.engine.db_statistics(
                    connection, name, self._column_key(column), column.get("properties", {}).get("dataType", "")
                )
            except TableTooLarge as e:
                entries.append(self._entry(dataset_id, statistics["id"], "Statistics", "B", SKIPPED_LARGE, started, detail=str(e)))
                continue
            except Exception as e:  # noqa: BLE001 - retried by a later run
                entries.append(self._entry(dataset_id, statistics["id"], "Statistics", "B", FAILED, started, detail=f"{type(e).__name__}: {e}"[:800]))
                continue
            self._store_statistics(dataset_id, table, column, statistics, computed, delta, entries, started)

    def _table_semantic_db(self, dataset_id, table, connection, targets, delta, entries) -> None:
        if not targets:
            return
        started = time.monotonic()
        names = [self._column_key(c) for c in targets]
        detail = ""
        try:
            annotations = self.engine.db_semantic_types(connection, self._table_name(table), names)
        except Exception as e:  # noqa: BLE001 - retried by a later run
            annotations, detail = None, f"{type(e).__name__}: {e}"[:800]
        self._store_semantic(dataset_id, table, targets, annotations, detail, self._column_key, delta, entries, started)

    def _store_semantic(self, dataset_id, table, targets, annotations, detail, key_of, delta, entries, started) -> None:
        for column in targets:
            key = key_of(column)
            previous = column.get("properties", {}).get("semanticType")
            if annotations is None:
                outcome, reason = FAILED, detail
            elif key not in annotations:
                outcome, reason = SKIPPED_MISSING, "column_not_annotated"
            elif annotations[key] == "error":
                outcome, reason = FAILED, "annotator_error"
            elif not usable_semantic_type(annotations[key]):
                # A deliberate "no label": the header already says what the column holds.
                outcome, reason = SKIPPED_EMPTY, "no_label"
            else:
                value = annotations[key]
                delta.link_column(table.record_set["id"], column["id"])
                delta.set_properties(column["id"], {"semanticType": value})
                entries.append(
                    self._entry(dataset_id, column["id"], "Column", "C", WRITTEN, started,
                                properties={"semanticType": value}, previous={"semanticType": previous})
                )
                continue
            entries.append(self._entry(dataset_id, column["id"], "Column", "C", outcome, started, detail=reason))

    # -- document record sets ---------------------------------------------------------

    def _wants_document(self, graph, record_set) -> bool:
        if "D" not in self.options.backfills:
            return False
        properties = record_set.get("properties", {})
        return is_blank(properties.get("keywords")) and "jsonShape" not in properties

    def _process_document(self, dataset_id, graph, record_set, delta, entries) -> None:
        started = time.monotonic()
        record_set_id = record_set["id"]

        def done(outcome: str, **extra) -> None:
            entries.append(self._entry(dataset_id, record_set_id, "RecordSet", "D", outcome, started, **extra))

        file_object, reason = match_document_file(graph, record_set)
        if file_object is None:
            done(SKIPPED_MISSING, detail=reason)
            return
        path = normalize_content_url(str(file_object.get("properties", {}).get("contentUrl", "")))
        problem = self._file_problem(path, file_object)
        if problem:
            done(problem[0], detail=problem[1])
            return

        name = document_stem(str(record_set["properties"].get("name", "")))
        try:
            text = self.engine.document_text(path, is_pdf=bool(set(file_object["labels"]) & PDF_FILE_LABELS))
            if len(text.split()) < self.engine.min_document_words:
                done(SKIPPED_EMPTY, detail="too_little_text")
                return
            description = self.engine.describe(text, name)
        except Exception as e:  # noqa: BLE001 - retried by a later run
            done(FAILED, detail=f"{type(e).__name__}: {e}"[:800])
            return

        properties: dict[str, Any] = {}
        if description.keywords:
            properties["keywords"] = list(description.keywords)
        if description.summary and is_blank(record_set["properties"].get("summary")):
            properties["summary"] = description.summary
        if not description.keywords:
            # describe_document turns every failure into an empty result.
            done(FAILED, detail="empty_llm_description")
            return
        delta.link_record_set(record_set_id)
        delta.set_properties(record_set_id, properties)
        previous = {k: record_set["properties"].get(k) for k in properties}
        done(WRITTEN, properties=properties, previous=previous)

    # -- sending the delta ------------------------------------------------------------

    def _apply(self, dataset_id: str, delta: Delta, entries: list[dict]) -> None:
        if delta.is_empty:
            self._flush(entries)
            return
        payload = delta.payload()
        if self.options.deltas_dir is not None:
            self.options.deltas_dir.mkdir(parents=True, exist_ok=True)
            (self.options.deltas_dir / f"{dataset_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        problem = self._send(dataset_id, delta, payload)
        if problem:
            for entry in entries:
                if entry["outcome"] in (WRITTEN, CLEAN):
                    entry.update(outcome=FAILED, detail=problem[:800], new_node_ids=[])
        self._flush(entries)

    def _send(self, dataset_id: str, delta: Delta, payload: dict) -> Optional[str]:
        """Validate and, when writing, store the delta. Returns what went wrong, if anything."""
        try:
            check_delta(delta)
            validation = self.moma.validate(payload)
        except Exception as e:  # noqa: BLE001 - reported per target through the ledger
            return f"validate: {e}"
        if validation.get("valid") is not True:
            return f"validate: {json.dumps(validation)[:700]}"
        if not self.options.write:
            return None
        try:
            self.moma.write(payload)
        except Exception as e:  # noqa: BLE001 - the read-back below decides what happened
            write_error = f"write: {e}"
        else:
            write_error = ""
        try:
            problems = verify_written(delta, Graph(self.moma.dataset(dataset_id)))
        except Exception as e:  # noqa: BLE001
            return f"read_back: {e}" + (f"; {write_error}" if write_error else "")
        if problems:
            return "read_back: " + "; ".join(problems[:10]) + (f"; {write_error}" if write_error else "")
        return None

    def _flush(self, entries: Iterable[dict]) -> None:
        for entry in entries:
            self.ledger.record(entry)


# -- Commands ----------------------------------------------------------------------------


def _client(env: str) -> MomaClient:
    session = requests.Session()
    return MomaClient(ENVIRONMENTS[env]["base_url"], TokenSource.from_environment(env, session), session)


def run(args: argparse.Namespace) -> int:
    if not args.dataset and not args.all:
        raise SystemExit("Name datasets with --dataset, or pass --all.")
    if args.write and args.env == "prod" and not args.confirm_prod:
        raise SystemExit("A production write needs --confirm-prod, after the dev results were reviewed.")
    if args.write and args.all and not args.confirm_all:
        raise SystemExit("Writing to every dataset needs --confirm-all.")

    backfills = set(args.only.split(",")) if args.only else set(BACKFILLS)
    if backfills - set(BACKFILLS):
        raise SystemExit(f"--only takes a comma separated subset of {','.join(BACKFILLS)}")

    run_id = args.run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    directory = Path(args.ledger_dir)
    ledger = Ledger(directory / f"{run_id}.jsonl", run_id, args.env, applied=args.write)
    options = Options(
        backfills=backfills,
        write=args.write,
        stop_on_unreadable=args.env == "prod",
        deltas_dir=directory / f"{run_id}-deltas",
    )
    moma = _client(args.env)
    engine = ProfilerEngine(args.db_statement_timeout, args.db_max_rows)
    backfiller = Backfiller(moma, engine, ledger, options, run_id, args.profiler_version)

    dataset_ids = list(args.dataset or moma.ready_dataset_ids())
    if args.limit:
        dataset_ids = dataset_ids[: args.limit]
    print(f"run {run_id}: {len(dataset_ids)} datasets, {'WRITE' if args.write else 'dry run'}, {args.env}")

    exit_code = 0
    try:
        for position, dataset_id in enumerate(dataset_ids, 1):
            print(f"[{position}/{len(dataset_ids)}] {dataset_id}", flush=True)
            try:
                backfiller.process(dataset_id)
            except StopRun:
                raise
            except Exception as e:  # noqa: BLE001 - one dataset must not stop the others
                traceback.print_exc()
                ledger.record(
                    {"dataset_id": dataset_id, "node_id": dataset_id, "node_kind": "Dataset",
                     "backfill": None, "outcome": FAILED, "detail": f"{type(e).__name__}: {e}"[:800]}
                )
    except StopRun as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        exit_code = 2
    finally:
        ledger.close()

    print(f"ledger: {ledger.path}")
    for (backfill, outcome), count in sorted(ledger.counts.items(), key=str):
        print(f"  {backfill or '-'} {outcome}: {count}")
    return exit_code


def rollback(args: argparse.Namespace) -> int:
    """Undo a run's property changes. New nodes are listed for CNRS to delete by id."""
    moma = _client(args.env)
    new_ids: list[str] = []
    undo: dict[str, dict] = defaultdict(dict)
    with open(args.ledger, encoding="utf-8") as ledger_file:
        for line in ledger_file:
            entry = json.loads(line)
            if not entry.get("applied"):
                continue
            new_ids.extend(entry.get("new_node_ids", []))
            previous = entry.get("previous", {})
            for key in entry.get("properties", {}):
                undo[entry["node_id"]][key] = previous.get(key)
    print(f"{len(undo)} nodes to restore, {len(new_ids)} new nodes to delete by id")
    for node_id, properties in undo.items():
        if args.write:
            moma.patch_node(node_id, properties)
        else:
            print(f"would PATCH {node_id}: {sorted(properties)}")
    if new_ids:
        print("New nodes, for deletion by CNRS:")
        print("\n".join(new_ids))
    return 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="backfill datasets (a dry run unless --write)")
    run_parser.add_argument("--env", choices=ENVIRONMENTS, required=True)
    run_parser.add_argument("--dataset", action="append", help="dataset id, repeatable")
    run_parser.add_argument("--all", action="store_true", help="every ready dataset")
    run_parser.add_argument("--only", help="subset of A,B,C,D (default: all four)")
    run_parser.add_argument("--limit", type=int, help="process at most this many datasets")
    run_parser.add_argument("--write", action="store_true", help="write to MoMa")
    run_parser.add_argument("--confirm-prod", action="store_true")
    run_parser.add_argument("--confirm-all", action="store_true")
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--ledger-dir", default="/tmp/backfill")
    run_parser.add_argument("--profiler-version", default=os.environ.get("PROFILER_VERSION", "unknown"))
    run_parser.add_argument("--db-statement-timeout", type=int, default=DEFAULT_DB_STATEMENT_TIMEOUT_SECONDS,
                            help="seconds a single database query may run")
    run_parser.add_argument("--db-max-rows", type=int, default=DEFAULT_DB_MAX_ROWS,
                            help="skip statistics on tables estimated to have more rows than this")
    run_parser.set_defaults(handler=run)

    rollback_parser = commands.add_parser("rollback", help="undo a run's property changes")
    rollback_parser.add_argument("--env", choices=ENVIRONMENTS, required=True)
    rollback_parser.add_argument("--ledger", required=True)
    rollback_parser.add_argument("--write", action="store_true", help="apply; otherwise only print")
    rollback_parser.set_defaults(handler=rollback)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
