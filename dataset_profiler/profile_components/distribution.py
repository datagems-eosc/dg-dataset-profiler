import mimetypes
import os
import uuid
from hashlib import sha256
from pathlib import Path

from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)
from dataset_profiler.configs.config_logging import logger

DATASET_ROOT_PATH = os.environ.get("DATA_ROOT_PATH", "")
SUPPORTED_EXTENSION_MAP = {
    ".csv": "text/csv",
    ".sql": "text/sql",
    ".db": "text/sql",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".xml": "application/xml",
    ".json": "application/json",
    ".jsonl": "application/jsonl",
    ".md": "text/markdown",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ipynb": "application/x-ipynb+json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# Files whose extension is absent from the map above are still listed in the
# distribution -- consumers need to know they exist and where they live -- they
# are just not opened for record set extraction, statistics or data quality.
FALLBACK_ENCODING_FORMAT = "application/octet-stream"


def is_supported(file_path: str | Path) -> bool:
    """Whether the profiler knows how to look inside a file of this type."""
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSION_MAP


def get_encoding_format(file_path: str | Path) -> str:
    """Best-effort MIME type for a file, from its extension alone.

    Supported types keep the exact value the profiler has always emitted, so
    downstream checks that compare against those strings are unaffected.
    Everything else falls back to the standard library's guess (``audio/mp4``
    for ``.m4a``, say) and finally to ``application/octet-stream``.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix in SUPPORTED_EXTENSION_MAP:
        return SUPPORTED_EXTENSION_MAP[suffix]
    guessed, _ = mimetypes.guess_type(Path(file_path).name)
    return guessed or FALLBACK_ENCODING_FORMAT


class DistributionFileObject:
    def __init__(
        self,
        file_object_id: str,
        name: str,
        description: str = "",
        content_size: str = "",
        content_url: str = "",
        encoding_format: str = "",
        sha256_check: str = "",
        contained_in: str | None = None,
    ):
        self.type = "cr:FileObject"
        self.id = file_object_id
        self.name = name
        self.description = description
        self.content_size = content_size
        self.content_url = content_url
        self.encoding_format = encoding_format
        self.sha256_check = sha256_check
        self.contained_in = contained_in
        self.is_minimal = False

    def to_dict(self):
        ret_dict = {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "contentSize": self.content_size,
            "contentUrl": self.content_url,
            "encodingFormat": self.encoding_format,
            "sha256": self.sha256_check,
        }
        if self.contained_in:
            ret_dict["containedIn"] = {"@id": self.contained_in}
        return ret_dict


def get_distribution_of_file_object(
    file_object: str, file_object_id: str
) -> DistributionFileObject:
    """
    Create a distribution object for a file.

    Every file gets an entry, whatever its type: the distribution is the
    dataset's inventory, so dropping a file here would hide it from consumers
    entirely. Files the profiler cannot read (audio, video, archives, ...) are
    flagged ``is_minimal`` so that record set extraction leaves them alone;
    they still carry their path, size and MIME type.
    """
    supported = is_supported(file_object)
    if not supported:
        logger.info(
            "Listing file without profiling it - unsupported file type",
            file=Path(file_object).name,
            file_extension=Path(file_object).suffix.lower(),
        )

    distribution = DistributionFileObject(
        file_object_id=file_object_id,
        name=file_object.split("/")[-1],
        content_size=f"{Path(file_object).stat().st_size} B",
        content_url=file_object,
        encoding_format=get_encoding_format(file_object),
        sha256_check=sha256(file_object.encode("utf-8")).hexdigest(),
    )
    distribution.is_minimal = not supported
    return distribution


class DistributionDatabaseConnection:
    def __init__(
        self,
        connection_id: str,
        database_name: str,
        protocol: str,
        engine: str,
        host: str,
        port: int,
        description: str = "",
    ):
        self.type = "dg:DatabaseConnection"
        self.id = connection_id
        self.name = database_name
        self.engine = engine
        self.description = description
        self.content_url = f"{protocol}://{host}:{port}/{database_name}"
        self.encoding_format = "text/sql"

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            # "databaseName": self.database_name,
            "contentUrl": self.content_url,
            "encodingFormat": self.encoding_format,
            "description": self.description,
        }


def get_distribution_of_database_connection(
    connection_id: str, database_name: str, protocol: str, engine: str, host: str, port: int
) -> DistributionDatabaseConnection:
    return DistributionDatabaseConnection(
        connection_id=connection_id,
        database_name=database_name,
        protocol=protocol,
        engine=engine,
        host=host,
        port=port,
    )


def get_distributions_of_tables_in_db(
    database_name: str, database_distribution_id: str, engine: str
) -> list[DistributionFileObject]:
    db = DatagemsPostgres(database=database_name, schema="public", engine=engine)
    tables = db.get_tables_and_columns()

    added_distributions = []
    for table in tables["tables"]:
        added_distributions.append(
            DistributionFileObject(
                file_object_id=str(uuid.uuid4()),
                name=table,
                contained_in=database_distribution_id,
                encoding_format="text/sql",
                content_url=f"{database_name}.public.{table}",
            )
        )

    return added_distributions


class DistributionFileSet:
    def __init__(
        self,
        file_set_id: str,
        name: str,
        description: str = "",
        content_size: str = "",
        encoding_format: str = "",
        includes: str = "",
        content_url: str = "",
    ):
        self.type = "cr:FileSet"
        self.id = file_set_id
        self.name = name
        self.description = description
        self.content_size = content_size
        self.content_url = content_url
        self.encoding_format = encoding_format
        self.includes = includes + "/*"

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "contentSize": self.content_size,
            "contentUrl": self.content_url,
            "encodingFormat": self.encoding_format,
            "includes": self.includes,
        }


def get_distribution_of_file_set(file_set, file_set_id) -> DistributionFileSet:
    """
    Create a distribution object for a file set (directory).

    A directory holding only unsupported files is still listed, otherwise the
    files inside it would disappear from the profile along with it. The set's
    encoding format is taken from the first file the profiler can read, so that
    mixed directories keep advertising their readable type; failing that, from
    the first file of any type.
    """
    files_in_dir = sorted(path for path in Path(file_set).glob("*") if path.is_file())
    sample_file_of_dir = next(
        (path for path in files_in_dir if is_supported(path)),
        next(iter(files_in_dir), None),
    )

    if sample_file_of_dir is None:
        logger.warning("Listing empty file set", file_set=file_set)
    elif not is_supported(sample_file_of_dir):
        logger.info(
            "Listing file set without profiling it - contains no supported file types",
            file_set=file_set,
        )

    return DistributionFileSet(
        file_set_id=file_set_id,
        name=file_set.split("/")[-1],
        content_size=f"{sum(path.stat().st_size for path in files_in_dir)} B",
        encoding_format=get_encoding_format(sample_file_of_dir) if sample_file_of_dir else "",
        includes=f"{file_set.split('/')[-1]}",
        content_url=file_set
    )


def get_file_objects_of_file_set(contained_in_id: str, file_set_path: str) -> list[DistributionFileObject]:
    file_objects = []
    for file_path in Path(file_set_path).glob("*"):
        if file_path.is_file():
            file_object = get_distribution_of_file_object(
                file_object=str(file_path),
                file_object_id=str(uuid.uuid4()),
            )
            file_object.contained_in = contained_in_id
            file_objects.append(file_object)
    return file_objects
