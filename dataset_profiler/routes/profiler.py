import uuid
import ray
from fastapi import APIRouter, HTTPException
from enum import Enum
from pydantic import BaseModel

from dataset_profiler.configs.config_reader import app_config
from dataset_profiler.job_manager import job_storing
from dataset_profiler.job_manager.profile_job import profile_job, endpoint_specification_to_dataset
from dataset_profiler.schemas.specification import ProfileSpecificationEndpoint

router = APIRouter(
    prefix=f"{app_config['fastapi']['base_url']}/profiler",
    tags=["Profiler"],
)


class IngestionTriggerResponse(BaseModel):
    job_id: str
    status: str

# In-memory task registry, we might want to replace this with Redis or a database later
TASKS = {}

@router.post("/trigger_profile")
async def trigger_dataset_profiling(
    profile_spec: ProfileSpecificationEndpoint,
) -> IngestionTriggerResponse:
    ingestion_job_id = str(uuid.uuid4())  # Not to be confused with the dataset id

    job_storing.store_job_status(ingestion_job_id, job_storing.JobStatus.SUBMITTING)
    obj_ref = profile_job.remote(ingestion_job_id, endpoint_specification_to_dataset(profile_spec))
    TASKS[ingestion_job_id] = obj_ref

    return IngestionTriggerResponse(
        job_id=ingestion_job_id,
        status="Job submitted",
    )


class RunnerStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


@router.get("/runner_status/{profile_job_id}")
async def get_runner_status(profile_job_id: str) -> RunnerStatus:
    obj_ref = TASKS.get(profile_job_id)
    if not obj_ref:
        return RunnerStatus.UNKNOWN

    ready, _ = ray.wait([obj_ref], timeout=0)
    if ready:
        _ = ray.get(obj_ref)
        return RunnerStatus.COMPLETED
    else:
        return RunnerStatus.IN_PROGRESS


@router.get("/job_status/{profile_job_id}")
async def get_job_status(profile_job_id: str) -> job_storing.JobStatus:
    return  job_storing.get_job_status(profile_job_id)


@router.get("/profile/{profile_job_id}")
async def get_profile(profile_job_id: str) -> job_storing.ProfilesResponse:
    response = job_storing.get_job_response(profile_job_id)

    if response is None:
        raise HTTPException(status_code=404, detail="No profile found for the given job ID. "
                                                    "Profiling might still be in progress.")
    return response
