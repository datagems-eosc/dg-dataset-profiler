import uuid
from typing import List, Optional

from pydantic import BaseModel


class RawDataPath(BaseModel):
    """
    Specifies a path to the raw data files for profiling.

    ## Attributes
    * **type** (str): The type of connector, must be "RawDataPath"
    * **dataset_id** (str): The unique identifier of the dataset in the storage system

    ## Example
    ```json
    {
        "type": "RawDataPath",
        "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
    }
    ```
    """
    type: str
    dataset_id: str


class DatabaseConnection(BaseModel):
    """
    Specifies connection details for a database to be profiled.

    ## Attributes
    * **type** (str): The type of connector, must be "DatabaseConnection"
    * **database_name** (str): The name of the database to connect to

    ## Example
    ```json
    {
        "type": "DatabaseConnection",
        "database_name": "ds_era5_land"
    }
    ```
    """
    type: str
    database_name: str


class ProfileSpecificationEndpoint(BaseModel):
    """
    Metadata about the dataset to be profiled.

    This class contains comprehensive metadata about a dataset, including its
    identification, description, and access methods.

    ## Attributes
    * **id** (uuid.UUID): Unique identifier for the dataset
    * **name** (str): Name of the dataset
    * **description** (str): Detailed description of the dataset
    * **headline** (str): Short headline describing the dataset
    * **fields_of_science** (List[str]): List of scientific fields based on OECD disciplines
    * **languages** (List[str]): List of languages used in the dataset (ISO 639 codes)
    * **keywords** (List[str]): List of keywords describing the dataset
    * **country** (str): Country code where the dataset originates
    * **published_url** (Optional[str]): URL where the dataset is published
    * **doi** (Optional[str]): Digital Object Identifier for the dataset
    * **date_published** (str): Publication date in format "DD-MM-YYYY"
    * **cite_as** (Optional[str]): Citation information
    * **license** (str): License information
    * **data_connectors** (List[Union[RawDataPath, DatabaseConnection]]): List of data connectors
    * **database_name** (Optional[str]): Name of the database (legacy field)
    * **uploaded_by** (str): User who uploaded the dataset

    ## Example
    ```json
    {
      "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
      "name": "Mathematics Learning Assessment",
      "description": "This dataset was extracted from the MathE platform...",
      "headline": "Dataset for Assessing Mathematics Learning in Higher Education.",
      "fields_of_science": ["MATHEMATICS"],
      "languages": ["en"],
      "keywords": ["math", "student", "higher education"],
      "country": "PT",
      "published_url": "https://dados.ipb.pt//dataset.xhtml?persistentId=doi:10.34620/dadosipb/PW3OWY",
      "doi": "",
      "date_published": "24-05-2025",
      "cite_as": "",
      "license": "CC0 1.0",
      "uploaded_by": "ADMIN",
      "data_connectors": [
        {
          "type": "RawDataPath",
          "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
        }
      ]
    }
    ```
    """
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

    data_connectors: List[RawDataPath | DatabaseConnection] = None
    database_name: str | None = None

    uploaded_by: str  # User who uploaded the dataset


class ProfilingRequest(BaseModel):
    """
    Request model for triggering a dataset profiling job.

    ## Attributes
    * **profile_specification** (ProfileSpecificationEndpoint): Metadata about the dataset to be profiled
    * **only_light_profile** (bool): Flag to generate only basic metadata (default: False)
      * If True, only the light profile (basic metadata and distributions) is generated
      * If False, both light and heavy profiles (including record sets) are generated

    ## Example
    ```json
    {
      "profile_specification": {
        "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
        "name": "Mathematics Learning Assessment",
        "description": "This dataset was extracted from the MathE platform...",
        "headline": "Dataset for Assessing Mathematics Learning in Higher Education.",
        "fields_of_science": ["MATHEMATICS"],
        "languages": ["en"],
        "keywords": ["math", "student", "higher education"],
        "country": "PT",
        "published_url": "https://dados.ipb.pt//dataset.xhtml?persistentId=doi:10.34620/dadosipb/PW3OWY",
        "date_published": "24-05-2025",
        "license": "CC0 1.0",
        "uploaded_by": "ADMIN",
        "data_connectors": [
          {
            "type": "RawDataPath",
            "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
          }
        ]
      },
      "only_light_profile": false
    }
    ```
    """
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
      "uploaded_by": "ADMIN",
      "data_connectors": [
        {
            "type": "RawDataPath",
            "dataset_id": "/home/ray/app/tests/assets/mathe_assessment/data"
        }
    ]
    },
  "only_light_profile": false
}

{
  "profile_specification":
    {
      "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
      "cite_as": "",
      "country": "PT",
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
      "uploaded_by": "ADMIN",
      "data_connectors": [
        {
          "type": "DatabaseConnection",
          "database_name": "ds_era5_land"
        }
      ]
    },
  "only_light_profile": false
}
"""
