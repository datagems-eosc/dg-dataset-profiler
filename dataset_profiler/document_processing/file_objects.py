"""Turn a FileObject id into a local PDF path, through MoMa, with the caller's token.

This is the interim answer to "FileObject id to path" agreed for the MathE
keywords flow: the profiler resolves the ids itself. A generic AP operator
that does it for every service is the long-term plan and will replace this
module, so everything about resolution stays here.

* MoMa's ``GET /nodes/{id}`` is called with the incoming bearer token, so MoMa
  checks the caller's grants (``dg_ds-browse`` on the parent dataset) and
  answers 404 when the node is unknown or not visible.
* Only the ``contentUrl`` MoMa returns is read, never one sent in the request.
* The path must lie under the dataset storage (``DATA_ROOT_PATH``) and, when the
  request names the dataset, under that dataset's folder.
"""

import os
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import quote

import pymupdf
import requests

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.document_processing.service import max_pages
from dataset_profiler.utilities import file_sha256

DEFAULT_MOMA_API_URL = "https://datagems-dev.scayle.es/moma2/v1"
DEFAULT_S3_MOUNT = "/s3"
MOMA_TIMEOUT_SECONDS = 30
# Header DataGEMS services use to log a request under one id across services.
CORRELATION_HEADER = "x-tracking-correlation"

PDF_MIME_TYPE = "application/pdf"
FILE_OBJECT_LABEL = "cr:FileObject"


class FileObjectError(Exception):
    """A FileObject that cannot be converted, with the HTTP status to answer."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class ResolvedFile:
    file_object_id: str
    path: str
    pages: int
    # Of the file's bytes, not the node's property: a profile can be stale.
    sha256: str


def moma_api_url() -> str:
    return (os.environ.get("MOMA_API_URL") or DEFAULT_MOMA_API_URL).rstrip("/")


def s3_mount() -> str:
    """Where the bucket is mounted: ``s3://X`` is ``<mount>/X``."""
    return (os.environ.get("DOCUMENT_S3_MOUNT") or DEFAULT_S3_MOUNT).rstrip("/")


def dataset_root() -> Optional[str]:
    """The dataset storage, ``/s3/dataset/`` in dev and prod (DATA_ROOT_PATH)."""
    return os.environ.get("DATA_ROOT_PATH") or None


def node_url(file_object_id: str) -> str:
    # The form in-dataset-discovery uses (text2sql4ap_service._moma_node_url).
    return f"{moma_api_url()}/api/nodes/{quote(file_object_id, safe='')}"


def fetch_node(file_object_id: str, token: Optional[str],
               correlation_id: Optional[str] = None) -> dict:
    """The FileObject's MoMa node, as the caller may see it."""
    headers = {"accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id
    try:
        response = requests.get(node_url(file_object_id), headers=headers,
                                timeout=MOMA_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        logger.error("MoMa unreachable", file_object_id=file_object_id, error=str(e))
        raise FileObjectError(424, "MoMa could not be reached to look up the FileObjects")

    if response.status_code == 404:
        raise FileObjectError(
            404, f"FileObject {file_object_id} was not found, or the caller may not see it")
    if response.status_code == 403:
        raise FileObjectError(403, f"MoMa refused access to FileObject {file_object_id}")
    if not response.ok:
        logger.error("MoMa error while looking up a FileObject", file_object_id=file_object_id,
                     status_code=response.status_code, response_text=response.text[:500])
        raise FileObjectError(424, f"MoMa answered {response.status_code} for FileObject "
                                   f"{file_object_id}")
    try:
        node = response.json()
    except ValueError:
        raise FileObjectError(424, f"MoMa returned an unreadable answer for FileObject "
                                   f"{file_object_id}")
    if not isinstance(node, dict):
        raise FileObjectError(424, f"MoMa returned an unreadable answer for FileObject "
                                   f"{file_object_id}")
    return node


def check_pdf(file_object_id: str, node: dict) -> str:
    """The node's contentUrl, or 400 unless the node is a PDF FileObject."""
    if FILE_OBJECT_LABEL not in (node.get("labels") or []):
        raise FileObjectError(400, f"Node {file_object_id} is not a FileObject")
    properties = node.get("properties") or {}
    content_url = properties.get("contentUrl")
    encoding = properties.get("encodingFormat")
    if (encoding != PDF_MIME_TYPE or not isinstance(content_url, str)
            or not content_url.lower().endswith(".pdf")):
        raise FileObjectError(
            400, f"FileObject {file_object_id} is not a PDF (encodingFormat {encoding!r}); "
                 f"only PDFs are converted")
    return content_url


def _under(path: str, folder: str) -> bool:
    return os.path.commonpath([path, folder]) == folder


def local_path(file_object_id: str, content_url: str, dataset_id: Optional[str] = None) -> str:
    """The real local path of a contentUrl, confined to the dataset storage.

    ``s3://X`` is ``/s3/X``, as for the Gateway. A mounted path (``/s3/...``),
    which profiles store, is taken as it is. Symlinks are resolved first.
    """
    root = dataset_root()
    if root is None:
        logger.error("DATA_ROOT_PATH is not set, FileObjects cannot be read")
        raise FileObjectError(503, "The dataset storage is not configured on this deployment")

    if content_url.startswith("s3://"):
        path = f"{s3_mount()}/{content_url[len('s3://'):]}"
    elif content_url.startswith(f"{DEFAULT_S3_MOUNT}/"):
        path = s3_mount() + content_url[len(DEFAULT_S3_MOUNT):]
    elif content_url.startswith("/"):
        path = content_url
    else:
        raise FileObjectError(400, f"FileObject {file_object_id} has no path on the dataset storage")
    if ".." in PurePosixPath(path).parts:
        raise FileObjectError(400, f"FileObject {file_object_id} is outside the dataset storage")

    real = os.path.realpath(path)
    allowed = os.path.realpath(root)
    if dataset_id is not None:
        allowed = os.path.realpath(os.path.join(allowed, dataset_id))
    if not _under(real, allowed):
        where = f"dataset {dataset_id}" if dataset_id else "the dataset storage"
        raise FileObjectError(400, f"FileObject {file_object_id} is not a file of {where}")
    return real


def inspect_pdf(file_object_id: str, path: str) -> tuple[int, str]:
    """Pages and content hash of the PDF: 404 when missing, 400 when unreadable or too long."""
    if not os.path.isfile(path):
        raise FileObjectError(404, f"The file of FileObject {file_object_id} is missing on storage")
    try:
        with pymupdf.open(path) as doc:
            pages = doc.page_count
    except Exception as e:  # noqa: BLE001 - reported as an unreadable PDF
        logger.warning("PDF cannot be opened", file_object_id=file_object_id, error=str(e))
        raise FileObjectError(400, f"The PDF of FileObject {file_object_id} cannot be opened")
    if pages > max_pages():
        raise FileObjectError(400, f"The PDF of FileObject {file_object_id} has {pages} pages; "
                                   f"at most {max_pages()} are accepted")
    return pages, file_sha256(path)


def check_dataset_id(dataset_id: Optional[str]) -> Optional[str]:
    """The dataset id as a canonical UUID; it becomes part of a path."""
    if dataset_id is None:
        return None
    try:
        return str(uuid.UUID(str(dataset_id)))
    except ValueError:
        raise FileObjectError(422, f"Dataset id {dataset_id!r} is not a UUID")


def resolve_file_object(file_object_id: str, token: Optional[str],
                        dataset_id: Optional[str] = None,
                        correlation_id: Optional[str] = None) -> ResolvedFile:
    """Look the FileObject up in MoMa and check its PDF. Blocking: run it in a thread."""
    node = fetch_node(file_object_id, token, correlation_id)
    content_url = check_pdf(file_object_id, node)
    path = local_path(file_object_id, content_url, dataset_id)
    pages, sha256 = inspect_pdf(file_object_id, path)
    recorded = (node.get("properties") or {}).get("sha256")
    if recorded and recorded != sha256:
        logger.warning("FileObject content differs from its profile's sha256",
                       file_object_id=file_object_id, profile_sha256=recorded, sha256=sha256)
    return ResolvedFile(file_object_id=file_object_id, path=path, pages=pages, sha256=sha256)
