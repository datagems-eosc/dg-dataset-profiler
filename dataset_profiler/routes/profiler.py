import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel

from dataset_profiler.configs.config_reader import app_config
from dataset_profiler.schemas.specification import ProfileSpecification

router = APIRouter(
    prefix=f"{app_config['fastapi']['base_url']}/profiler",
    tags=["Profiler"],
)


class IngestionTriggerResponse(BaseModel):
    job_id: str


@router.post("/trigger_profile")
async def trigger_dataset_profiling(
    profile_spec: ProfileSpecification,
) -> IngestionTriggerResponse:
    ingestion_job_id = str(uuid.uuid4())  # To not be confused with the dataset id
    return IngestionTriggerResponse(job_id=ingestion_job_id)


class ProfileStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@router.get("/status/{profile_job_id}")
async def trigger_dataset_profiling(profile_job_id: str) -> ProfileStatus:
    return ProfileStatus.COMPLETED
