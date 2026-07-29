import uuid
import ray
from fastapi import APIRouter, HTTPException, Depends
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any

from dataset_profiler.job_manager import job_storing
from dataset_profiler.job_manager import ray_client
from dataset_profiler.job_manager.profile_job import profile_job, endpoint_specification_to_dataset
from dataset_profiler.schemas.specification import ProfilingRequest
from dataset_profiler.configs.config_logging import logger
from dataset_profiler.routes.auth import validate_token, get_token_if_enabled


router = APIRouter(
    prefix=f"/profiler",
    tags=["Profiler"],
)


class IngestionTriggerResponse(BaseModel):
    """
    Response model for a submitted profiling job.

    ## Attributes
    * **job_id**: Unique identifier for tracking the profiling job
    * **status**: Confirmation message that the job was submitted

    ## Example
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "Job submitted"
    }
    ```
    """
    job_id: str
    status: str

# In-memory task registry, we might want to replace this with Redis or a database later
TASKS = {}

@router.post("/trigger_profile")
async def trigger_dataset_profiling(
    profile_req: ProfilingRequest,
    token: Optional[Dict[str, Any]] = Depends(validate_token)
) -> IngestionTriggerResponse:
    """
    Submit a new dataset profiling job.

    This endpoint accepts dataset specifications and initiates a profiling job. The profiling process
    analyzes the dataset structure and content, generating metadata that describes its characteristics.

    ## Parameters
    * **profile_req** (ProfilingRequest): The profiling request containing:
      * profile_specification: Metadata about the dataset to be profiled
      * only_light_profile: Flag to generate only basic metadata (default: False)

    ## Returns
    * **IngestionTriggerResponse**: A response containing:
      * job_id: Unique identifier for tracking the profiling job
      * status: Confirmation message that the job was submitted

    ## Example
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "Job submitted"
    }
    ```
    """
    ingestion_job_id = str(uuid.uuid4())  # Not to be confused with the dataset id
    logger.info("Received Profiling Request", request=profile_req, ingestion_job_id=ingestion_job_id)

    # Reconnect to Ray on demand if the connection dropped (e.g. the Ray head was
    # restarted). This lets jobs succeed again automatically without an API restart.
    if not ray_client.ensure_connection():
        logger.error("Ray cluster unavailable, cannot submit profiling job", ingestion_job_id=ingestion_job_id)
        raise HTTPException(
            status_code=503,
            detail="Ray cluster is currently unavailable. Please retry shortly.",
        )

    job_storing.store_job_status(ingestion_job_id, job_storing.JobStatus.SUBMITTING)
    job_storing.store_job_dataset_id(ingestion_job_id, str(profile_req.profile_specification.id))
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
    """
    Enumeration of possible Ray task statuses.

    ## Values
    * **PENDING**: The job is waiting to be processed
    * **IN_PROGRESS**: The job is currently being processed
    * **COMPLETED**: The job has completed successfully
    * **FAILED**: The job has failed
    * **UNKNOWN**: The job ID is not recognized
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


@router.get("/runner_status/{profile_job_id}")
async def get_runner_status(
    profile_job_id: str,
    token: Optional[Dict[str, Any]] = Depends(validate_token)
) -> RunnerStatus:
    """
    Check the status of the Ray task for a given profiling job.

    This endpoint queries the Ray cluster to determine the current execution status of a profiling task.
    It provides information about whether the task is pending, in progress, completed, failed, or unknown.

    ## Parameters
    * **profile_job_id** (str): The unique identifier of the profiling job

    ## Returns
    * **RunnerStatus**: The current status of the Ray task, one of:
      * pending: The job is waiting to be processed
      * in_progress: The job is currently being processed
      * completed: The job has completed successfully
      * failed: The job has failed
      * unknown: The job ID is not recognized

    ## Example
    ```
    "in_progress"
    ```
    """
    logger.info("Received runner status request", profile_job_id=profile_job_id)
    obj_ref = TASKS.get(profile_job_id)
    if not obj_ref:
        return RunnerStatus.UNKNOWN

    if not ray_client.ensure_connection():
        logger.warning("Ray cluster unavailable while checking runner status", profile_job_id=profile_job_id)
        raise HTTPException(
            status_code=503,
            detail="Ray cluster is currently unavailable. Please retry shortly.",
        )

    try:
        ready, _ = ray.wait([obj_ref], timeout=0)
        logger.info("Runner status", profile_job_id=profile_job_id, ready=ready)
        if ready:
            _ = ray.get(obj_ref)
            # Release the object ref promptly so the Ray object store can reclaim
            # the memory (the Ray head is memory capped).
            TASKS.pop(profile_job_id, None)
            del obj_ref
            return RunnerStatus.COMPLETED
        else:
            return RunnerStatus.IN_PROGRESS
    except Exception as ex:
        # The object ref belongs to a previous Ray session (the head was
        # restarted), so its result is no longer retrievable. Persisted status
        # in Redis (job_status) remains the source of truth for clients.
        logger.warning("Could not read runner status from Ray", profile_job_id=profile_job_id, error=str(ex))
        return RunnerStatus.UNKNOWN


@router.get("/job_status/{profile_job_id}")
async def get_job_status(
    profile_job_id: str,
    token: Optional[Dict[str, Any]] = Depends(validate_token)
) -> job_storing.JobStatusResponse:
    """
    Check the detailed status of a profiling job.

    This endpoint retrieves the current status of a profiling job from the job store.
    It provides more detailed information about the job's progress than the runner status.

    ## Parameters
    * **profile_job_id** (str): The unique identifier of the profiling job

    ## Returns
    * **JobStatusResponse**: The current status report, containing:
      * status: The current status of the profiling job, one of:
        * SUBMITTING: The job is being submitted to the processing queue
        * STARTING: The job has been accepted and is starting
        * LIGHT_PROFILE_READY: The light profile (basic metadata) is ready
        * HEAVY_PROFILES_READY: The heavy profile (including record sets) is ready
        * FAILED: The job has failed
      * dataset_id: The identifier of the dataset being profiled (or None if unknown)

    ## Example
    ```json
    {
      "status": "light_profile_ready",
      "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
    }
    ```
    """
    logger.info("Received job status request", profile_job_id=profile_job_id)
    status = job_storing.get_job_status(profile_job_id)
    dataset_id = job_storing.get_job_dataset_id(profile_job_id)
    logger.info("Job status", profile_job_id=profile_job_id, status=status, dataset_id=dataset_id)
    return job_storing.JobStatusResponse(status=status, dataset_id=dataset_id)


@router.get("/profile/{profile_job_id}")
async def get_profile(
    profile_job_id: str,
    token: Optional[Dict[str, Any]] = Depends(validate_token)
) -> job_storing.ProfilesResponse:
    """
    Retrieve the generated profile for a completed profiling job.

    This endpoint returns the profile data generated for a dataset, including both light and heavy profiles
    if available. The profile contains metadata about the dataset structure, content, and characteristics.

    ## Parameters
    * **profile_job_id** (str): The unique identifier of the profiling job

    ## Returns
    * **ProfilesResponse**: The generated profiles, containing:
      * moma_profile_light: Basic metadata about the dataset and its distributions
      * moma_profile_heavy: Detailed information about record sets and fields
      * cdd_profile: Profile used by the Cross-Dataset Discovery service

    ## Raises
    * **HTTPException**: 404 Not Found if no profile exists for the given job ID or if profiling is still in progress

    ## Example
    ```json
    {
      "moma_profile_light": {
        "@context": {...},
        "@type": "sc:Dataset",
        "name": "Mathematics Learning Assessment",
        "description": "...",
        "distribution": [...]
      },
      "moma_profile_heavy": {
        "@context": {...},
        "@type": "sc:Dataset",
        "recordSet": [...]
      },
      "cdd_profile": {}
    }
    ```
    """
    logger.info("Received profile get request", profile_job_id=profile_job_id)
    response = job_storing.get_job_response(profile_job_id)

    if response is None:
        logger.warning("No profile found for the given job ID. Profiling might still be running.",
                       profile_job_id=profile_job_id)
        raise HTTPException(status_code=404, detail="No profile found for the given job ID. "
                                                    "Profiling might still be in progress.")

    logger.info("Found profile entry", profile_job_id=profile_job_id)
    return response


class CddProfilePathResponse(BaseModel):
    """
    Response model for the CDD profile path lookup by dataset ID.

    ## Attributes
    * **cdd_profile_path** (Optional[str]): The path to the CDD profile JSON file, or None if not ready yet
    """
    cdd_profile_path: Optional[str]


@router.get("/cdd_profile_path/{dataset_id}")
async def get_cdd_profile_path_by_dataset_id(
    dataset_id: str,
    token: Optional[Dict[str, Any]] = Depends(validate_token)
) -> CddProfilePathResponse:
    """
    Retrieve the CDD profile path for a dataset by its dataset ID.

    The CDD profile file is written once the heavy profile completes. This endpoint allows
    consumers that only know the dataset ID (not the profiling job ID) to retrieve the path.

    ## Parameters
    * **dataset_id** (str): The dataset identifier used when the profiling job was submitted

    ## Returns
    * **CddProfilePathResponse**: Contains the CDD profile path, or None if the profile is not ready yet
    """
    logger.info("Received CDD profile path request", dataset_id=dataset_id)
    cdd_profile_path = job_storing.get_cdd_profile_path(dataset_id)
    if cdd_profile_path is None:
        logger.info("CDD profile path not ready yet", dataset_id=dataset_id)
        return CddProfilePathResponse(cdd_profile_path=None)

    logger.info("Found CDD profile path", dataset_id=dataset_id, cdd_profile_path=cdd_profile_path)
    return CddProfilePathResponse(cdd_profile_path=cdd_profile_path)


class CleanUpRequest(BaseModel):
    """
    Request model for cleaning up resources associated with a profiling job.

    ## Attributes
    * **profile_job_id** (str): The unique identifier of the profiling job to clean up

    ## Example
    ```json
    {
      "profile_job_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```
    """
    profile_job_id: str


@router.post("/clean_up")
async def clean_up_job(
    clean_up_req: CleanUpRequest,
    token: Optional[Dict[str, Any]] = Depends(validate_token)
) -> dict:
    """
    Clean up resources associated with a completed profiling job.

    This endpoint releases resources and temporary storage used during the profiling process.
    It should be called after retrieving and storing the profile data to free up system resources.

    ## Parameters
    * **clean_up_req** (CleanUpRequest): Request containing:
      * profile_job_id: The unique identifier of the profiling job to clean up

    ## Returns
    * **dict**: A response indicating the success of the cleanup operation

    ## Example
    ```json
    {
      "detail": "SUCCESS"
    }
    ```

    ## Note
    This endpoint is currently a placeholder and cleanup functionality is not yet implemented.
    """
    logger.warning("Received clean up request. Clean up is not implemented yet.", profile_job_id=clean_up_req.profile_job_id)
    return {"detail": "SUCCESS"}
