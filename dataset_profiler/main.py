import uvicorn
import os
import ray

from dataset_profiler.configs.config_reader import app_config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dataset_profiler.routes.add_routes import initialize_routes

# Connect to Ray cluster (the head node)
RAY_ADDRESS = os.getenv("RAY_ADDRESS", "ray://ray-head:10001")
if not ray.is_initialized():
    ray.init(address=RAY_ADDRESS, ignore_reinit_error=True)

app = FastAPI(
    version="0.0.1",
    root_path=os.getenv("BASE_URL", "")
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


@app.get("/")
def read_root():
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
