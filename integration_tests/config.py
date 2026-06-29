"""Configuration for the API integration tests.

Unlike the unit tests under ``tests/`` (which import ``DatasetProfile`` directly),
these tests exercise the *running* HTTP API end to end. They submit real
profiling jobs to the API (which dispatches them to the Ray cluster) and assert
on the returned profiles.

How the dataset path is resolved
--------------------------------
The API receives a ``data_connector`` of type ``RawDataPath`` whose
``dataset_id`` is a path. On the Ray worker the path is resolved relative to
``DATA_ROOT_PATH`` (``/home/ray/app/tests/assets/`` in ``docker-compose-dev.yml``,
which mounts the repo's ``./tests`` directory). Therefore the ``dataset_id`` sent
to the API must be **relative to ``tests/assets/``** (e.g. ``zoo_24/data``), NOT
the ``tests/assets/zoo_24/data`` form used by the unit-test ``specifications.json``
files (those bypass the endpoint transformation).

``LOCAL_ASSETS_ROOT`` below points at the same ``tests/assets`` directory on the
host, so the test suite can verify each configured path actually exists before
hitting the API.
"""
import os
from pathlib import Path

# Base URL of the running API (see docker-compose-dev.yml: api -> host port 8000).
BASE_URL = os.getenv("PROFILER_API_URL", "http://localhost:8000")

# The API guards every endpoint with an HTTPBearer dependency, so a token must be
# present even when ENABLE_AUTH is false (in which case the value is not verified).
AUTH_TOKEN = os.getenv("PROFILER_API_TOKEN", "test-token")

# Host-side location of the dataset assets. The Ray worker resolves RawDataPath
# dataset_ids relative to this directory (mounted at /home/ray/app/tests/assets/).
LOCAL_ASSETS_ROOT = Path(__file__).resolve().parents[1] / "tests" / "assets"

# How long to wait for a job to reach a terminal state, and how often to poll.
# The first job after a cold start can be slow (Ray worker warm-up), so the
# timeout is generous.
JOB_TIMEOUT_SECONDS = int(os.getenv("PROFILER_JOB_TIMEOUT", "300"))
POLL_INTERVAL_SECONDS = float(os.getenv("PROFILER_POLL_INTERVAL", "3"))


# Each entry describes a dataset to profile through the API plus the properties we
# expect to see in the resulting profile. ``data_path`` is the path relative to
# ``tests/assets/`` and is sent verbatim to the API as the RawDataPath dataset_id.
DATASETS = [
    {
        "id": "zoo_2024",
        "dataset_id": "11111111-1111-1111-1111-111111111111",
        "name": "ZOO 2024 Dataset",
        "description": "Counts of animals kept in zoos in 2024.",
        "headline": "Zoo animal population counts for 2024.",
        "fields_of_science": ["MATHEMATICS"],
        "languages": ["en"],
        "keywords": ["animals", "zoo"],
        "country": "PT",
        "data_path": "zoo_24/data",
        # Expectations
        "expected_files": ["zoo-2024.csv"],
        "expected_record_set": "zoo-2024",
        "expected_fields_contain": ["Art", "Anzahl", "Kommune"],
    },
    {
        "id": "mathe_assessment",
        "dataset_id": "22222222-2222-2222-2222-222222222222",
        "name": "Mathematics Learning Assessment",
        "description": (
            "Student responses to mathematics questions from the MathE platform."
        ),
        "headline": "Dataset for Assessing Mathematics Learning in Higher Education.",
        "fields_of_science": ["MATHEMATICS"],
        "languages": ["en"],
        "keywords": ["math", "student", "higher education"],
        "country": "PT",
        "data_path": "mathe_assessment/data",
        # Expectations
        "expected_files": ["mathe_assessment_dataset.csv"],
        "expected_record_set": "mathe_assessment_dataset",
        "expected_fields_contain": [
            "Student ID",
            "Student Country",
            "Question ID",
            "Type of Answer",
        ],
    },
    {
        "id": "subway_data",
        "dataset_id": "33333333-3333-3333-3333-333333333333",
        "name": "Subway Validations Dataset",
        "description": "Subway validation counts per station and route.",
        "headline": "Subway data.",
        "fields_of_science": ["CIVIL ENGINEERING"],
        "languages": ["el"],
        "keywords": ["subway", "transport"],
        "country": "GR",
        "data_path": "subway_data/data",
        # Expectations
        "expected_files": ["csv_1.csv"],
        "expected_record_set": "csv_1",
        "expected_fields_contain": ["dv_agency", "dv_validations", "dv_route"],
    },
]


def build_request(dataset: dict, only_light_profile: bool = False) -> dict:
    """Build the ``ProfilingRequest`` JSON body for a configured dataset."""
    return {
        "profile_specification": {
            "id": dataset["dataset_id"],
            "name": dataset["name"],
            "description": dataset["description"],
            "headline": dataset["headline"],
            "fields_of_science": dataset["fields_of_science"],
            "languages": dataset["languages"],
            "keywords": dataset["keywords"],
            "country": dataset["country"],
            "date_published": "2025-08-23",
            "license": "CC0 1.0",
            "uploaded_by": "ADMIN",
            "data_connectors": [
                {"type": "RawDataPath", "dataset_id": dataset["data_path"]}
            ],
        },
        "only_light_profile": only_light_profile,
    }
