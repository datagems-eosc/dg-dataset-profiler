import uuid
import time
import ray
from typing import Annotated
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel

from dataset_profiler.configs.config_reader import app_config
from dataset_profiler.profile_models import DatasetProfile
from dataset_profiler.schemas.specification import ProfileSpecification

router = APIRouter(
    prefix=f"{app_config['fastapi']['base_url']}/profiler",
    tags=["Profiler"],
)


class IngestionTriggerResponse(BaseModel):
    job_id: str
    status: str

# In-memory task registry, we might want to replace this with Redis or a database later
TASKS = {}

@ray.remote
def profile_job(specification: dict):
    profile = DatasetProfile(specification)

    # Send the dataset head with distribution to DMM
    profile.extract_distributions()
    light_profile = profile.to_dict_light()
    print("Sending light profile to DMM...")
    print(light_profile)

    # Send the full profile to DMM
    profile.extract_record_sets()
    heavy_profile = profile.to_dict()

    print("Sending heavy profile to DMM...")
    print(heavy_profile)

    return heavy_profile


@router.post("/trigger_profile")
async def trigger_dataset_profiling(
    profile_spec: ProfileSpecification,
) -> IngestionTriggerResponse:
    ingestion_job_id = str(uuid.uuid4())  # To not be confused with the dataset id
    obj_ref = profile_job.remote(profile_spec.model_dump())
    TASKS[ingestion_job_id] = obj_ref

    return IngestionTriggerResponse(
        job_id=ingestion_job_id,
        status="Job submitted",
    )


class ProfileStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


@router.get("/status/{profile_job_id}")
async def trigger_dataset_profiling(profile_job_id: str) -> ProfileStatus:
    obj_ref = TASKS.get(profile_job_id)
    if not obj_ref:
        return ProfileStatus.UNKNOWN

    ready, _ = ray.wait([obj_ref], timeout=0)
    if ready:
        _ = ray.get(obj_ref)
        return ProfileStatus.COMPLETED
    else:
        return ProfileStatus.IN_PROGRESS
