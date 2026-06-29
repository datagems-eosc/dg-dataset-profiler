import os
import threading

import uvicorn

from dataset_profiler.configs.config_reader import app_config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dataset_profiler.routes.add_routes import initialize_routes
from dataset_profiler.job_manager import ray_client

# NOTE: We deliberately do NOT call ray.init() at import time. The Ray head is
# memory capped and may be unavailable when this process starts; a failed
# connection here would crash the web server (exit 1 -> CrashLoopBackOff). The
# connection is established in the startup hook below and re-established lazily
# on demand (see dataset_profiler.job_manager.ray_client).
RAY_ADDRESS = ray_client.RAY_ADDRESS

app = FastAPI(
    version="0.0.1",
    root_path=os.getenv("BASE_URL", ""),
    openapi_url="/openapi.json",
    docs_url="/swagger",
    redoc_url="/redoc",
)
from dataset_profiler.configs.config_logging import logger
logger.info(
    "Starting Dataset Profiler Service",
    root_path=os.getenv("BASE_URL", ""),
    ray_address=RAY_ADDRESS,
    version="0.0.1",
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
#     allow_credentials=False,
# )

initialize_routes(app)


@app.on_event("startup")
def connect_ray_on_startup():
    """Try to connect to Ray in the background with retry/backoff.

    This must never block the server from coming up nor crash it: if Ray is down
    the API still serves requests and reconnects lazily when Ray returns.
    """
    threading.Thread(
        target=ray_client.connect_with_retry,
        name="ray-startup-connect",
        daemon=True,
    ).start()


@app.get("/")
def read_root():
    """Pure HTTP liveness endpoint -- does not depend on Ray.

    Suitable as a Kubernetes readiness/liveness probe target so that a transient
    Ray outage never deregisters this pod from the Service.
    """
    logger.info("Root endpoint accessed")
    return {"message": "Welcome!"}


def main():
    uvicorn.run(
        "dataset_profiler.main:app",
        host=app_config["fastapi"]["host"],
        port=app_config["fastapi"]["port"],
        reload=app_config["fastapi"]["debug"],
        workers=app_config["fastapi"]["workers"],
        reload_dirs=["dataset_profiler/"],
    )


if __name__ == "__main__":
    main()
