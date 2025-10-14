import uvicorn
import os
import ray

from dataset_profiler.configs.config_reader import app_config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dataset_profiler.routes.add_routes import initialize_routes

# Connect to Ray cluster (the head node)
RAY_ADDRESS = os.getenv("RAY_ADDRESS", "ray://ray-head:10001")
ray.init(address=RAY_ADDRESS, ignore_reinit_error=True)

app = FastAPI(
    openapi_url=app_config["fastapi"]["base_url"] + "/openapi.json",
    docs_url=app_config["fastapi"]["base_url"] + "/docs",
    redoc_url=app_config["fastapi"]["base_url"] + "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

initialize_routes(app)


@app.get("/")
def read_root():
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
