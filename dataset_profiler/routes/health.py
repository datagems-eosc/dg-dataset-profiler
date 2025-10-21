from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from dataset_profiler.configs.config_reader import app_config
from dataset_profiler.job_manager.job_storing import redis_health_check
from dataset_profiler.job_manager.profile_job import ray_health_check

router = APIRouter(
    prefix=f"{app_config['fastapi']['base_url']}/monitoring",
    tags=["Health"],
)


@router.get("/health-check")
async def check_health() -> dict:
    redis_status = redis_health_check()
    ray_status = ray_health_check()
    status_report = {
        "redis": redis_status,
        "ray": ray_status,
    }
    if redis_status['status'] == 'healthy' and ray_status['status'] == 'healthy':
        return status_report
    else:
        raise HTTPException(status_code=503, detail=status_report)
