import uuid
import ray
from fastapi import APIRouter, HTTPException
from enum import Enum
from pydantic import BaseModel

from dataset_profiler.job_manager import job_storing
from dataset_profiler.job_manager.profile_job import profile_job, endpoint_specification_to_dataset
from dataset_profiler.schemas.specification import ProfilingRequest
from dataset_profiler.configs.config_logging import logger


router = APIRouter(
    prefix=f"/profiler",
    tags=["Profiler"],
)


class IngestionTriggerResponse(BaseModel):
    job_id: str
    status: str

# In-memory task registry, we might want to replace this with Redis or a database later
TASKS = {}

@router.post("/trigger_profile")
async def trigger_dataset_profiling(
    profile_req: ProfilingRequest,
) -> IngestionTriggerResponse:
    ingestion_job_id = str(uuid.uuid4())  # Not to be confused with the dataset id
    logger.info(f"Received Profiling Request", request=profile_req, ingestion_job_id=ingestion_job_id)

    job_storing.store_job_status(ingestion_job_id, job_storing.JobStatus.SUBMITTING)
    obj_ref = profile_job.remote(ingestion_job_id,
                                 endpoint_specification_to_dataset(profile_req.profile_specification),
                                 only_light_profile=profile_req.only_light_profile)
    TASKS[ingestion_job_id] = obj_ref
    logger.info("Submitted profiling job to Ray", ingestion_job_id=ingestion_job_id)
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
    logger.info(f"Received runner status request", profile_job_id=profile_job_id)
    obj_ref = TASKS.get(profile_job_id)
    if not obj_ref:
        return RunnerStatus.UNKNOWN

    ready, _ = ray.wait([obj_ref], timeout=0)
    logger.info(f"Runner status", profile_job_id=profile_job_id, ready=ready)
    if ready:
        _ = ray.get(obj_ref)
        return RunnerStatus.COMPLETED
    else:
        return RunnerStatus.IN_PROGRESS


@router.get("/job_status/{profile_job_id}")
async def get_job_status(profile_job_id: str) -> job_storing.JobStatus:
    logger.info(f"Received job status request", profile_job_id=profile_job_id)
    status = job_storing.get_job_status(profile_job_id)
    logger.info(f"Job status", profile_job_id=profile_job_id, status=status)
    return status


@router.get("/profile/{profile_job_id}")
async def get_profile(profile_job_id: str) -> job_storing.ProfilesResponse:
    logger.info(f"Received profile get request", profile_job_id=profile_job_id)
    response = job_storing.get_job_response(profile_job_id)

    if response is None:
        logger.warning(f"No profile found for the given job ID. Profiling might still be running.",
                       profile_job_id=profile_job_id)
        raise HTTPException(status_code=404, detail="No profile found for the given job ID. "
                                                    "Profiling might still be in progress.")

    logger.info(f"Found profile entry", profile_job_id=profile_job_id)
    return response


class CleanUpRequest(BaseModel):
    profile_job_id: str


@router.post("/clean_up}")
async def clean_up_job(profile_job_id: CleanUpRequest) -> dict:
    logger.warning(f"Received clean up request. Clean up is not implmeneted yet.", profile_job_id=profile_job_id)
    return {"detail": "SUCCESS"}
