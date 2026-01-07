import os
import uuid
from hashlib import sha256
from pathlib import Path

from dataset_profiler.profile_components.record_set.db.database_connector import DatagemsPostgres

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
        contained_in: str = None
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
) -> DistributionFileObject:
    file_extension = Path(file_object).suffix

    sha = sha256(file_object.encode("utf-8")).hexdigest()

    if file_extension == ".csv":
        encoding_format = "text/csv"
    elif file_extension == ".sql" or file_extension == ".db":
        encoding_format = "text/sql"
    elif file_extension == ".xlsx":
        encoding_format = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise ValueError("Unsupported file type for distribution: " + file_extension)

    return DistributionFileObject(
        file_object_id=file_object_id,
        name=file_object.split("/")[-1],
        content_size=f"{Path(file_object).stat().st_size} B",
        content_url=f"s3:/{DATASET_ROOT_PATH}{file_object.split('/')[-1]}",
        encoding_format=encoding_format,
        sha256_check=sha,
    )


class DistributionDatabaseConnection:
    def __init__(
        self,
        connection_id: str,
        database_name: str,
        description: str = "",
    ):
        self.type = "dg:DatabaseConnection"
        self.id = connection_id
        self.name = database_name
        self.description = description
        self.encodingFormat = "text/sql"

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            # "databaseName": self.database_name,
            "encodingFormat": self.encodingFormat,
            "description": self.description
        }


def get_distribution_of_database_connection(
    connection_id: str, database_name: str
) -> DistributionDatabaseConnection:
    return DistributionDatabaseConnection(
        connection_id=connection_id,
        database_name=database_name,
    )

def get_distributions_of_tables_in_db(database_name: str, database_distribution_id: str) -> list[DistributionFileObject]:
    db = DatagemsPostgres(database=database_name, schema="public")
    tables = db.get_tables_and_columns()

    added_distributions = []
    for table in tables['tables']:
        added_distributions.append(
            DistributionFileObject(
                file_object_id=str(uuid.uuid4()),
                name=table,
                contained_in=database_distribution_id,
                encoding_format="text/sql"
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
        self.content_url = "s3:/" + DATASET_ROOT_PATH + includes
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
    sample_file_of_dir = next(Path(file_set).glob("*"), None)

    if sample_file_of_dir.suffix.lower() in [".png", ".jpg", ".jpeg"]:
        encoding_format = "image/" + sample_file_of_dir.suffix[1:]
    elif sample_file_of_dir.suffix.lower() == ".pdf":
        encoding_format = "application/pdf"
    elif sample_file_of_dir.suffix.lower() == ".txt":
        encoding_format = "text/plain"
    elif sample_file_of_dir.suffix.lower() == ".pptx":
        encoding_format = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif sample_file_of_dir.suffix.lower() == ".docx":
        encoding_format = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif sample_file_of_dir.suffix.lower() == ".ipynb":
        encoding_format = "application/x-ipynb+json"
    else:
        raise ValueError(
            "Unsupported file type for file in file set: " + sample_file_of_dir.suffix
        )

    file_sizes = [
        os.path.getsize(file_set + "/" + f)
        for f in os.listdir(file_set)
        if os.path.isfile(file_set + "/" + f)
    ]
    return DistributionFileSet(
        file_set_id=file_set_id,
        name=file_set.split("/")[-1],
        content_size=f"{sum(file_sizes)} B",
        encoding_format=encoding_format,
        includes=f"{file_set.split('/')[-1]}",
    )
