import os
import uuid
import logging
from hashlib import sha256
from pathlib import Path

from dataset_profiler.profile_components.record_set.db.database_connector import (
    DatagemsPostgres,
)

DATASET_ROOT_PATH = os.environ.get("DATA_ROOT_PATH", "")


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
) -> DistributionFileObject | None:
    """
    Create a distribution object for a file.
    Returns None for unsupported file types to allow graceful skipping.
    """
    file_extension = Path(file_object).suffix.lower()

    sha = sha256(file_object.encode("utf-8")).hexdigest()

    # Map file extensions to MIME types
    extension_map = {
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
    }

    # If extension is not supported, skip this file
    if file_extension not in extension_map:
        logging.warning(f"Skipping unsupported file type: {Path(file_object).name}")
        return None

    encoding_format = extension_map[file_extension]

    return DistributionFileObject(
        file_object_id=file_object_id,
        name=file_object.split("/")[-1],
        content_size=f"{Path(file_object).stat().st_size} B",
        content_url=file_object,
        encoding_format=encoding_format,
        sha256_check=sha,
    )


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
    ):
        self.type = "cr:FileSet"
        self.id = file_set_id
        self.name = name
        self.description = description
        self.content_size = content_size
        self.content_url = DATASET_ROOT_PATH + includes
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


def get_distribution_of_file_set(file_set, file_set_id) -> DistributionFileSet | None:
    """
    Create a distribution object for a file set (directory).
    Returns None if no supported files are found in the directory.
    """
    # Find first supported file in directory
    supported_extensions = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".ipynb": "application/x-ipynb+json",
        ".html": "text/html",
        ".xml": "application/xml",
    }

    sample_file_of_dir = None
    encoding_format: str | None = None

    for file_path in Path(file_set).glob("*"):
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            if suffix in supported_extensions:
                sample_file_of_dir = file_path
                encoding_format = supported_extensions[suffix]
                break

    # If no supported files found in directory, skip this file set
    if sample_file_of_dir is None:
        logging.warning(
            f"Skipping file set '{file_set}' - contains no supported file types"
        )
        return None

    file_sizes = [
        os.path.getsize(file_set + "/" + f)
        for f in os.listdir(file_set)
        if os.path.isfile(file_set + "/" + f)
    ]
    return DistributionFileSet(
        file_set_id=file_set_id,
        name=file_set.split("/")[-1],
        content_size=f"{sum(file_sizes)} B",
        encoding_format=encoding_format or "",
        includes=f"{file_set.split('/')[-1]}",
    )


def get_file_objects_of_file_set(contained_in_id: str, file_set_path: str) -> list[DistributionFileObject]:
    file_objects = []
    for file_path in Path(file_set_path).glob("*"):
        if file_path.is_file():
            file_object = get_distribution_of_file_object(
                file_object=str(file_path),
                file_object_id=str(uuid.uuid4()),
            )
            if file_object:
                file_object.contained_in = contained_in_id
                file_objects.append(file_object)
    return file_objects
