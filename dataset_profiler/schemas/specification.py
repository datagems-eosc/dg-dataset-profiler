import uuid
from typing import List, Optional

from pydantic import BaseModel


class ProfileSpecification(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    headline: str
    fields_of_science: List[
        str
    ]  # Based on https://www.britishcouncil.cl/sites/default/files/oecd_disciplines_british_council.pdf
    languages: List[str]
    keywords: List[str]
    country: str
    published_url: Optional[str] = ""
    doi: Optional[str] = ""  # Can be the same as the published_url if the published_url is a DOI
    cite_as: Optional[str] = (
        ""  # Official abbreviations https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
    )
    license: str

    data_uri: str  # URI to the S3 bucket containing the raw dataset
    open: bool
