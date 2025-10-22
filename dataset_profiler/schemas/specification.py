import uuid
from typing import List, Optional

from pydantic import BaseModel


class ProfileSpecificationEndpoint(BaseModel):
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
    date_published: str  # YYYY-MM-DD
    cite_as: Optional[str] = (
        ""  # Official abbreviations https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
    )
    license: str

    dataset_file_path: str | None = None  # In deployed service case it should only be the same as the id field
    database_name: str | None = None

    uploaded_by: str  # User who uploaded the dataset


class ProfilingRequest(BaseModel):
    profile_specification: ProfileSpecificationEndpoint
    only_light_profile: bool = False


"""
Example request:
{
  "profile_specification":
    {
      "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
      "cite_as": "",
      "country": "PT",
      "data_uri": "tests/assets/mathe_assessment/data/",
      "date_published": "24-05-2025",
      "description": "This dataset was extracted from the MathE platform, an online educational platform developed to support mathematics teaching and learning in higher education. It contains 546 student responses to questions on several mathematical topics. Each record corresponds to an individual answer and includes the following features: Student ID, Student Country, Question ID, Type of Answer (correct or incorrect), Question Level (basic or advanced based on the assessment of the contributing professor), Math Topic (broader mathematical area of the question), Math Subtopic, and Question Keywords. The data spans from February 2019 to December 2023.",
      "fields_of_science": [
        "MATHEMATICS"
      ],
      "headline": "Dataset for Assessing Mathematics Learning in Higher Education.",
      "languages": [
        "en"
      ],
      "keywords": [
        "math",
        "student",
        "higher education"
      ],
      "license": "CC0 1.0",
      "name": "Mathematics Learning Assessment",
      "published_url": "https://dados.ipb.pt//dataset.xhtml?persistentId=doi:10.34620/dadosipb/PW3OWY",
      "uploaded_by": "ADMIN"
    },
  "only_light_profile": false
}
"""
