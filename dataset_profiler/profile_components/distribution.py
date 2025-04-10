from datetime import datetime
from hashlib import sha256
from pathlib import Path


class Distribution:
    def __init__(
        self,
        name: str,
        description: str = "",
        content_size: str = "",
        content_url: str = "",
        encoding_format: str = "",
        sha256_check: str = "",
    ):
        self.type = "cr:FileObject"
        self.id = sha256(str(datetime.now()).encode("utf-8")).hexdigest()
        self.name = name
        self.description = description
        self.content_size = content_size
        self.content_url = content_url
        self.encoding_format = encoding_format
        self.sha256_check = sha256_check

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "contentSize": self.content_size,
            "contentUrl": self.content_url,
            "encodingFormat": self.encoding_format,
            "sha256": self.sha256_check,
        }


def get_distribution(file_object) -> Distribution:
    file_extension = Path(file_object).suffix

    sha = sha256(file_object.encode("utf-8")).hexdigest()

    if file_extension == ".csv":
        encoding_format = "text/csv"
    elif file_extension == ".sql" or file_extension == ".db":
        encoding_format = "text/sql"
    else:
        encoding_format = "text"

    return Distribution(
        name=file_object.split("/")[-1],
        content_size=f"{Path(file_object).stat().st_size} B",
        content_url="",
        encoding_format=encoding_format,
        sha256_check=sha,
    )
