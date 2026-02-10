import os

from typing import Optional


DATASET_ROOT_PATH = os.environ.get("DATA_ROOT_PATH", "")

class DatasetTopLevel:
    def __init__(
        self,
        dataset_id: str,
        name: str,
        description: str = "",
        conforms_to: str = "",
        cite_as: str = "",
        license: str = "",
        url: str = "",
        doi: str = "",
        version: str = "",
        headline: str = "",
        keywords: Optional[list] = None,
        field_of_science: Optional[list] = None,
        in_language: Optional[list] = None,
        country: str = "",
        date_published: str = "",
        access: str = "PRIVATE", # PRIVATE or PUBLIC
        uploaded_by: str = ""
    ):
        self.type = "sc:Dataset"
        self.id = dataset_id
        self.name = name
        self.description = description
        self.conforms_to = conforms_to
        self.cite_as = cite_as
        self.license = license
        self.url = url
        self.doi = doi
        self.version = version
        self.headline = headline
        self.keywords = keywords if keywords is not None else []
        self.field_of_science = field_of_science if field_of_science is not None else []
        self.in_language = in_language if in_language is not None else []
        self.country = country
        self.date_published = date_published
        self.access = access
        self.uploaded_by = uploaded_by

    def to_dict(self):
        return {
            "@type": self.type,
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "sc:archivedAt": "s3:/" + DATASET_ROOT_PATH + self.id,
            "conformsTo": self.conforms_to,
            "citeAs": self.cite_as,
            "license": self.license,
            "url": self.url,
            "dg:doi": self.doi,
            "version": self.version,
            "dg:headline": self.headline,
            "dg:keywords": self.keywords,
            "dg:fieldOfScience": self.field_of_science,
            "inLanguage": self.in_language,
            "country": self.country,
            "datePublished": self.date_published,
            "dg:access": "",  # PROFILER DOES NOT DEFINE ACCESS LEVEL
            "dg:status": "loaded",
            "dg:uploadedBy": self.uploaded_by,
        }
