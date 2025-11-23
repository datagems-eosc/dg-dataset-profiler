from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from dataset_profiler.configs.config_reader import app_config
from dataset_profiler.job_manager.job_storing import redis_health_check
from dataset_profiler.job_manager.profile_job import ray_health_check
from dataset_profiler.configs.config_logging import logger

router = APIRouter(
    prefix=f"/monitoring",
    tags=["Health"],
)


@router.get("/health-check")
async def check_health() -> dict:
    """
    Check the health status of the Dataset Profiler service and its dependencies.

    This endpoint verifies the connectivity and operational status of critical service dependencies:

    * **Redis**: Used for job status tracking and caching
    * **Ray**: Used for distributed computing tasks

    ## Returns
    A status report containing health information for each dependency:
    * redis: Status and connection details
    * ray: Status and cluster information

    ## Raises
    * **HTTPException**: 503 Service Unavailable if any dependency is unhealthy

    ## Example
    ```json
    {
        "redis": {
            "status": "healthy",
            "message": "Connected to Redis at localhost:6379"
        },
        "ray": {
            "status": "healthy",
            "message": "Ray cluster reachable with 3 alive node(s)"
        }
    }
    ```
    """
    logger.info("Health check endpoint accessed")
    redis_status = redis_health_check()
    ray_status = ray_health_check()
    status_report = {
        "redis": redis_status,
        "ray": ray_status,
    }
    if redis_status['status'] == 'healthy' and ray_status['status'] == 'healthy':
        logger.info("Health check passed", report=status_report)
        return status_report
    else:
        logger.info("Health check failed", report=status_report)
        raise HTTPException(status_code=503, detail=status_report)
