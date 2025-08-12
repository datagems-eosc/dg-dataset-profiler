from typing import Annotated
from fastapi import APIRouter, Depends

from dataset_profiler.configs.config_reader import app_config

router = APIRouter(
    prefix=f"{app_config['fastapi']['base_url']}/monitoring",
    tags=["Health"],
)


@router.get("/health")
async def check_health():
    return True
