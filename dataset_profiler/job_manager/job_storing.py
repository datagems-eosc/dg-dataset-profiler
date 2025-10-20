import json
import os
from enum import Enum

import redis
from pydantic import BaseModel


class JobStatus(Enum):
    SUBMITTING = "submitting"
    STARTING = "starting"
    LIGHT_PROFILE_READY = "light_profile_ready"
    HEAVY_PROFILES_READY = "heavy_profile_ready"
    CLEANED_UP = "cleaned_up"


class ProfilesResponse(BaseModel):
    moma_profile_light: dict
    moma_profile_heavy: dict
    cdd_profile: dict


JOB_STATUS_GROUP = "job_status"
JOB_RESPONSE_GROUP = "job_response"


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
