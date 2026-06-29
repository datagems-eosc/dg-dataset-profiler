from fastapi import APIRouter

from dataset_profiler.job_manager.job_storing import redis_health_check
from dataset_profiler.job_manager.ray_client import health_status as ray_health_status
from dataset_profiler.configs.config_logging import logger

router = APIRouter(
    prefix=f"/monitoring",
    tags=["Health"],
)


@router.get("/ready")
async def readiness() -> dict:
    """Lightweight readiness probe that does NOT depend on Ray (or Redis).

    Kubernetes should point the readiness probe here (or at ``GET /``). A
    transient Ray outage must never deregister this pod from the Service, so
    readiness is decoupled from dependency health. Dependency status is reported
    separately by ``/monitoring/health-check``.
    """
    return {"status": "ready"}


@router.get("/health-check")
async def check_health() -> dict:
    """
    Report the health status of the Dataset Profiler service and its dependencies.

    This endpoint verifies the connectivity and operational status of critical service dependencies:

    * **Redis**: Used for job status tracking and caching
    * **Ray**: Used for distributed computing tasks

    It is purely diagnostic: it ALWAYS returns HTTP 200 from a live pod and never
    calls ``ray.init()``. A dependency being down is surfaced inside the response
    body (``status: degraded``) rather than as a 503, so this endpoint can be hit
    by callers (or a probe) without a Ray/Redis outage tearing the pod out of the
    Service. Use ``/monitoring/ready`` or ``GET /`` for readiness.

    ## Returns
    A status report containing health information for each dependency plus an
    overall status:
    * status: "healthy" if all dependencies are healthy, otherwise "degraded"
    * redis: Status and connection details
    * ray: Status and cluster information

    ## Example
    ```json
    {
        "status": "degraded",
        "redis": {
            "status": "healthy",
            "message": "Connected to Redis server successfully."
        },
        "ray": {
            "status": "degraded",
            "message": "Ray not connected: ..."
        }
    }
    ```
    """
    logger.info("Health check endpoint accessed")
    redis_status = redis_health_check()
    # NOTE: ray_health_status() probes the EXISTING Ray connection and never
    # calls ray.init(); it reconnects once cleanly if the connection is stale.
    ray_status = ray_health_status()

    overall = (
        "healthy"
        if redis_status["status"] == "healthy" and ray_status["status"] == "healthy"
        else "degraded"
    )
    status_report = {
        "status": overall,
        "redis": redis_status,
        "ray": ray_status,
    }
    logger.info("Health check completed", report=status_report)
    return status_report
