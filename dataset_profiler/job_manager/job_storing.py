import json
import os
from enum import Enum
from typing import Optional

import redis
from pydantic import BaseModel


class JobStatus(Enum):
    """
    Enumeration of possible profiling job statuses.

    ## Values
    * **SUBMITTING**: The job is being submitted to the processing queue
    * **STARTING**: The job has been accepted and is starting
    * **LIGHT_PROFILE_READY**: The light profile (basic metadata) is ready
    * **HEAVY_PROFILES_READY**: The heavy profile (including record sets) is ready
    * **CLEANED_UP**: Resources associated with the job have been cleaned up
    * **FAILED**: The job failed to complete
    """
    SUBMITTING = "submitting"
    STARTING = "starting"
    LIGHT_PROFILE_READY = "light_profile_ready"
    HEAVY_PROFILES_READY = "heavy_profile_ready"
    CLEANED_UP = "cleaned_up"
    FAILED = "failed"

class ProfilesResponse(BaseModel):
    """
    Response model containing the generated profiles for a dataset.

    ## Attributes
    * **moma_profile_light** (dict): Basic metadata about the dataset and its distributions
    * **moma_profile_heavy** (dict): Detailed information about record sets and fields
    * **cdd_profile** (dict): Profile used by the Cross-Dataset Discovery service

    ## Example
    ```json
    {
      "moma_profile_light": {
        "@context": {
          "@language": "en",
          "@vocab": "https://schema.org/",
          "cr": "http://mlcommons.org/croissant/"
        },
        "@type": "sc:Dataset",
        "name": "Mathematics Learning Assessment",
        "description": "This dataset was extracted from the MathE platform...",
        "distribution": [
          {
            "@type": "cr:FileObject",
            "name": "mathe_assessment_dataset.csv",
            "contentSize": "1057461 B",
            "encodingFormat": "text/csv"
          }
        ]
      },
      "moma_profile_heavy": {
        "@context": {
          "@language": "en",
          "@vocab": "https://schema.org/",
          "cr": "http://mlcommons.org/croissant/"
        },
        "@type": "sc:Dataset",
        "recordSet": [
          {
            "@type": "cr:RecordSet",
            "name": "mathe_assessment_dataset",
            "field": [
              {
                "@type": "cr:Field",
                "name": "Student ID",
                "dataType": "sc:Integer"
              }
            ]
          }
        ]
      },
      "cdd_profile": {}
    }
    ```
    """
    moma_profile_light: dict
    moma_profile_heavy: dict
    cdd_profile: dict


class JobStatusResponse(BaseModel):
    """
    Status report for a profiling job.

    ## Attributes
    * **status** (JobStatus): The current status of the profiling job
    * **dataset_id** (Optional[str]): The identifier of the dataset being profiled,
      or None if it was not recorded for the job

    ## Example
    ```json
    {
      "status": "light_profile_ready",
      "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
    }
    ```
    """
    status: JobStatus
    dataset_id: Optional[str] = None


JOB_STATUS_GROUP = "job_status"
JOB_RESPONSE_GROUP = "job_response"
JOB_DATASET_ID_GROUP = "job_dataset_id"
CDD_PROFILE_PATH_GROUP = "cdd_profile_path"


def get_redis_client():
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))

    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    return client


def store_job_status(job_id: str, status: JobStatus):
    client = get_redis_client()
    client.hset(JOB_STATUS_GROUP, job_id, status.value)


def get_job_status(job_id: str) -> JobStatus | None:
    client = get_redis_client()
    status_value = client.hget(JOB_STATUS_GROUP, job_id).decode("utf-8")
    if status_value is None:
        return None
    return JobStatus(status_value)


def store_job_dataset_id(job_id: str, dataset_id: str):
    client = get_redis_client()
    client.hset(JOB_DATASET_ID_GROUP, job_id, dataset_id)


def get_job_dataset_id(job_id: str) -> str | None:
    client = get_redis_client()
    dataset_id_value = client.hget(JOB_DATASET_ID_GROUP, job_id)
    if dataset_id_value is None:
        return None
    return dataset_id_value.decode("utf-8")


def store_job_response(job_id: str, response: ProfilesResponse):
    client = get_redis_client()
    client.hset(JOB_RESPONSE_GROUP, job_id, json.dumps(response.model_dump()))


def get_job_response(job_id: str) -> ProfilesResponse | None:
    client = get_redis_client()
    response_value = client.hget(JOB_RESPONSE_GROUP, job_id)
    if response_value is None:
        return None
    response_model = ProfilesResponse.model_validate(json.loads(response_value))
    return response_model


def store_cdd_profile_path(dataset_id: str, cdd_profile_path: str):
    client = get_redis_client()
    client.hset(CDD_PROFILE_PATH_GROUP, dataset_id, cdd_profile_path)


def get_cdd_profile_path(dataset_id: str) -> str | None:
    client = get_redis_client()
    path_value = client.hget(CDD_PROFILE_PATH_GROUP, dataset_id)
    if path_value is None:
        return None
    return path_value.decode("utf-8")


def redis_health_check() -> dict:
    try:
        client = get_redis_client()
        client.ping()
        return {
            "status": "healthy",
            "message": "Connected to Redis server successfully.",
        }
    except redis.exceptions.ConnectionError as e:
        return {
            "status": "error",
            "message": f"Cannot connect to Redis server. Error: {str(e)}",
            "configuration": {
                "REDIS_HOST": os.getenv("REDIS_HOST", "redis"),
                "REDIS_PORT": os.getenv("REDIS_PORT", "6379"),
                "REDIS_DB": os.getenv("REDIS_DB", "0"),
            }
        }
