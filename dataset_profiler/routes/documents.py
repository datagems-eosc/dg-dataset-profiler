"""MathE document endpoints: convert PDF FileObjects of a dataset to Markdown.

``POST /documents/convert4ap`` is the AP operator that DMM, the Task
Orchestrator, calls in the MathE keywords flow (Gateway, then DMM, then this
operator, then in-dataset-discovery's keyword matching). ``POST
/documents/convert`` does the same without an AP, for testing.

One request, one response: nothing to poll. Each FileObject is looked up in
MoMa with the caller's token (``file_objects``), converted in its own Ray task,
and kept in a cache (``markdown_cache``). The handler never blocks its event
loop: MoMa, Redis and Ray calls run in threads.
"""

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import ray
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.document_processing.ap_payload import (
    APError,
    parse_convert_ap,
    write_error,
    write_result,
)
from dataset_profiler.document_processing.file_objects import (
    CORRELATION_HEADER,
    FileObjectError,
    ResolvedFile,
    check_dataset_id,
    resolve_file_object,
)
from dataset_profiler.document_processing.markdown_cache import cache_key, get_cached
from dataset_profiler.document_processing.service import ConversionMode, ConvertResult
from dataset_profiler.job_manager import ray_client
from dataset_profiler.job_manager.document_job import CONVERSION_FAILED, convert_document_task
from dataset_profiler.routes.document_auth import bearer_token, require_document_access

# Below DMM's 300 s timeout for the services it calls.
DEFAULT_REQUEST_TIMEOUT_SECONDS = 240.0
DEFAULT_MAX_FILES = 20

router = APIRouter(prefix="/documents", tags=["MathE Documents"])


def request_timeout_seconds() -> float:
    value = os.environ.get("DOCUMENT_REQUEST_TIMEOUT_SECONDS")
    return float(value) if value else DEFAULT_REQUEST_TIMEOUT_SECONDS


def max_files() -> int:
    value = os.environ.get("DOCUMENT_MAX_FILES")
    return int(value) if value else DEFAULT_MAX_FILES


@dataclass
class FileOutcome:
    file_object_id: str
    sha256: str
    result: Optional[ConvertResult] = None
    error: Optional[str] = None


def _http_error(e: FileObjectError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


async def _resolve(file_object_ids: List[str], token: Optional[str], dataset_id: Optional[str],
                   correlation_id: Optional[str]) -> List[ResolvedFile]:
    """Every FileObject's PDF, looked up in parallel; the first failing id, in request order, wins."""
    found = await asyncio.gather(
        *(asyncio.to_thread(resolve_file_object, i, token, dataset_id, correlation_id)
          for i in file_object_ids),
        return_exceptions=True,
    )
    for item in found:
        if isinstance(item, FileObjectError):
            raise _http_error(item)
        if isinstance(item, BaseException):
            raise item
    return list(found)


def _collect(refs: list) -> List[dict]:
    """The tasks' answers; a task that crashed counts as a failed conversion."""
    answers = []
    for ref in refs:
        try:
            answers.append(ray.get(ref))
        except Exception as e:  # noqa: BLE001 - reported on the file, never raised
            logger.error("Document conversion task crashed", error=str(e))
            answers.append({"error": CONVERSION_FAILED})
    return answers


async def convert_file_objects(file_object_ids: List[str], mode: ConversionMode,
                               dataset_id: Optional[str], token: Optional[str],
                               correlation_id: Optional[str], deadline: float) -> List[FileOutcome]:
    """Convert the FileObjects' PDFs, from the cache when possible. Raises HTTPException."""
    try:
        dataset_id = check_dataset_id(dataset_id)
    except FileObjectError as e:
        raise _http_error(e)
    files = await _resolve(file_object_ids, token, dataset_id, correlation_id)

    keys = [cache_key(f.sha256, mode) for f in files]
    distinct = list(dict.fromkeys(keys))
    cached = await asyncio.gather(*(asyncio.to_thread(get_cached, k) for k in distinct))
    results: Dict[str, ConvertResult] = {k: r for k, r in zip(distinct, cached) if r is not None}
    errors: Dict[str, str] = {}

    # One task per distinct content: two ids for the same bytes are converted once.
    pending = {k: f for k, f in zip(keys, files) if k not in results}
    if pending:
        if not await asyncio.to_thread(ray_client.ensure_connection):
            logger.error("Ray cluster unavailable, cannot convert documents")
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                "Ray cluster is currently unavailable. Please retry shortly.")
        refs = await asyncio.to_thread(lambda: [
            convert_document_task.remote(f.path, mode.value, k, f.file_object_id)
            for k, f in pending.items()
        ])
        remaining = max(0.0, deadline - time.monotonic())
        _, not_ready = await asyncio.to_thread(ray.wait, refs, num_returns=len(refs),
                                               timeout=remaining)
        if not_ready:
            # The tasks go on and fill the cache: a retry is served from it.
            logger.warning("Document conversion exceeded the request timeout",
                           unfinished=len(not_ready), timeout_seconds=request_timeout_seconds())
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                f"The conversion takes longer than {request_timeout_seconds():.0f} s. It goes on: "
                f"retry later and finished files are served from the cache.")
        for key, answer in zip(pending, await asyncio.to_thread(_collect, refs)):
            if answer.get("result") is not None:
                results[key] = ConvertResult.model_validate(answer["result"])
            else:
                errors[key] = answer.get("error") or CONVERSION_FAILED

    return [FileOutcome(file_object_id=f.file_object_id, sha256=f.sha256,
                        result=results.get(k), error=errors.get(k))
            for k, f in zip(keys, files)]


def _check_file_count(count: int) -> None:
    if count > max_files():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"{count} files requested; at most {max_files()} per request")


def _log_outcomes(endpoint: str, mode: ConversionMode, outcomes: List[FileOutcome],
                  claims: Optional[Dict[str, Any]], started: float) -> None:
    logger.info("Converted documents", endpoint=endpoint, mode=mode.value,
                files=len(outcomes), failed=sum(o.error is not None for o in outcomes),
                seconds=round(time.monotonic() - started, 1),
                user_id=(claims or {}).get("sub"), client_id=(claims or {}).get("azp"))


AP_EXAMPLE = {
    "ap": {
        "nodes": [
            {"id": "6f1c2a4e-0b7d-4c1e-9a52-3d1f0e8b7a10", "labels": ["Analytical_Pattern"],
             "properties": {"name": "MathE document keywords"}},
            {"id": "a3e5d9c2-71f4-4b8e-8c0a-5e2b9d4f6c11",
             "labels": ["Document_Convert_Operator", "Operator"],
             "properties": {"name": "Convert to Markdown", "mode": "quality"}},
            {"id": "0c9b7e65-2f3a-4d18-b6e4-9a1c5d7e8f12", "labels": ["sc:Dataset"]},
            {"id": "5b2d8f17-9c4e-4a63-8d1b-7e0f2a6c9d13", "labels": ["cr:FileObject"]},
            {"id": "e7a4c1b9-3d6f-4e2a-9b5c-1f8d0e6a7b14", "labels": ["ResultType"],
             "properties": {"name": "markdown",
                            "fileObjectId": "5b2d8f17-9c4e-4a63-8d1b-7e0f2a6c9d13"}},
        ],
        "edges": [
            {"from": "6f1c2a4e-0b7d-4c1e-9a52-3d1f0e8b7a10",
             "to": "a3e5d9c2-71f4-4b8e-8c0a-5e2b9d4f6c11", "labels": ["consist_of"]},
            {"from": "0c9b7e65-2f3a-4d18-b6e4-9a1c5d7e8f12",
             "to": "5b2d8f17-9c4e-4a63-8d1b-7e0f2a6c9d13", "labels": ["distribution"]},
            {"from": "a3e5d9c2-71f4-4b8e-8c0a-5e2b9d4f6c11",
             "to": "5b2d8f17-9c4e-4a63-8d1b-7e0f2a6c9d13", "labels": ["input"]},
            {"from": "a3e5d9c2-71f4-4b8e-8c0a-5e2b9d4f6c11",
             "to": "e7a4c1b9-3d6f-4e2a-9b5c-1f8d0e6a7b14", "labels": ["output"]},
        ],
    }
}

ERRORS = """
## Errors
* **400**: a FileObject is not a PDF, cannot be opened, has more than
  DOCUMENT_MAX_PAGES pages, or lies outside the dataset storage or the named dataset
* **401** / **403**: missing or invalid token, missing role, or MoMa refused access
* **404**: a FileObject is unknown or not visible to the caller, or its file is
  missing on storage
* **422**: malformed request or AP, or more than DOCUMENT_MAX_FILES files
* **424**: MoMa unreachable or failing
* **503**: Ray, the identity provider or the dataset storage unavailable
* **504**: DOCUMENT_REQUEST_TIMEOUT_SECONDS (240) exceeded. The conversion goes
  on and fills the cache, so a retry is answered from it

The first failing FileObject, in request order, gives the error. A conversion
that fails on the vision model's side (every page failed) does not fail the
request: it is reported on that file only.
"""


CONVERT4AP_DESCRIPTION = """
The document conversion operator of an Analytical Pattern.

Reads the `Document_Convert_Operator` node, its `mode` ("quality", the
default, or "fast") and the `cr:FileObject` nodes it takes as `input` (only
their ids are used). Fills the Markdown `ResultType` node of each file,
the operator's `output` with properties `name` "markdown" and
`fileObjectId`:

* `value`: the Markdown; `pages`; `model`; `fallbackPages` (pages that kept
  the PDF's text layer after the vision model failed on them); `sha256` of
  the file;
* or `error`, when that file's conversion failed.

Every other node, edge and property is returned unchanged. When the AP has
an `sc:Dataset` node (the one distributing the files, or its only one), the
files must belong to that dataset.
""" + ERRORS


@router.post("/convert4ap", description=CONVERT4AP_DESCRIPTION,
             responses={200: {"content": {"application/json": {"example": AP_EXAMPLE}}}})
async def convert4ap(
    request: Request,
    payload: Dict[str, Any] = Body(..., examples=[AP_EXAMPLE]),
    claims: Optional[Dict[str, Any]] = Depends(require_document_access),
    token: Optional[str] = Depends(bearer_token),
) -> JSONResponse:
    """The document conversion operator of an Analytical Pattern."""
    started = time.monotonic()
    try:
        ap = parse_convert_ap(payload)
    except APError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    _check_file_count(len(ap.file_object_ids))

    outcomes = await convert_file_objects(
        ap.file_object_ids, ap.mode, ap.dataset_id, token,
        request.headers.get(CORRELATION_HEADER), started + request_timeout_seconds())
    for outcome in outcomes:
        node = ap.outputs[outcome.file_object_id]
        if outcome.result is not None:
            write_result(node, outcome.result, outcome.sha256)
        else:
            write_error(node, outcome.error or CONVERSION_FAILED, outcome.sha256)
    _log_outcomes("convert4ap", ap.mode, outcomes, claims, started)
    return JSONResponse(payload)


class ConvertRequest(BaseModel):
    """
    Convert PDF FileObjects of a dataset to Markdown.

    ## Attributes
    * **fileObjectIds**: the FileObjects, 1 to DOCUMENT_MAX_FILES (20)
    * **mode**: "quality" (default) reads every page with a vision model:
      scans, handwriting and formulas as LaTeX, several seconds per page.
      "fast" reads the PDF's text on the CPU, with OCR for scanned pages:
      about a second per document, but no handwriting and no LaTeX
    * **datasetId**: optional; the files must then belong to this dataset

    ## Example
    ```json
    {"fileObjectIds": ["5b2d8f17-9c4e-4a63-8d1b-7e0f2a6c9d13"], "mode": "quality"}
    ```
    """
    fileObjectIds: List[str] = Field(min_length=1)
    mode: ConversionMode = ConversionMode.QUALITY
    datasetId: Optional[str] = None


class ConvertedFile(BaseModel):
    """
    One converted FileObject: its Markdown, or the error.

    ## Attributes
    * **fileObjectId**: the FileObject
    * **markdown**: the document as Markdown, with LaTeX math in quality mode
    * **pages**: number of pages
    * **model**: the vision model, or "" in fast mode
    * **fallbackPages**: pages that kept the PDF's text layer after the vision model failed on them
    * **sha256**: of the file's content
    * **error**: why the conversion failed, or null
    """
    fileObjectId: str
    markdown: Optional[str] = None
    pages: Optional[int] = None
    model: Optional[str] = None
    fallbackPages: List[int] = Field(default_factory=list)
    sha256: str
    error: Optional[str] = None


class ConvertResponse(BaseModel):
    """The converted FileObjects, in request order."""
    files: List[ConvertedFile]


CONVERT_DESCRIPTION = """
Convert PDF FileObjects to Markdown without an Analytical Pattern.

Same lookup, conversion, cache and errors as /documents/convert4ap.
""" + ERRORS


@router.post("/convert", description=CONVERT_DESCRIPTION)
async def convert(
    request: Request,
    body: ConvertRequest,
    claims: Optional[Dict[str, Any]] = Depends(require_document_access),
    token: Optional[str] = Depends(bearer_token),
) -> ConvertResponse:
    """Convert PDF FileObjects to Markdown without an Analytical Pattern."""
    started = time.monotonic()
    file_object_ids = list(dict.fromkeys(body.fileObjectIds))
    _check_file_count(len(file_object_ids))
    outcomes = await convert_file_objects(
        file_object_ids, body.mode, body.datasetId, token,
        request.headers.get(CORRELATION_HEADER), started + request_timeout_seconds())
    _log_outcomes("convert", body.mode, outcomes, claims, started)
    return ConvertResponse(files=[
        ConvertedFile(
            fileObjectId=o.file_object_id,
            sha256=o.sha256,
            error=o.error,
            **({} if o.result is None else {
                "markdown": o.result.markdown, "pages": o.result.pages,
                "model": o.result.model, "fallbackPages": o.result.fallback_pages}),
        )
        for o in outcomes
    ])
