import argparse
import logging
from logging.config import dictConfig
from typing import Dict

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

logger = logging.getLogger("dataset_profiler")


def read_configs() -> Dict:
    parser = argparse.ArgumentParser(description="Dataset Profiler API.")
    parser.add_argument(
        "--config_file",
        help="path to config file",
        type=str,
    )

    try:
        config_file = parser.parse_args().config_file
    except SystemExit:
        config_file = None

    if config_file is None:
        logger.warning(
            "Could not parse a config value. The default config file will be used."
        )
        config_file = "dataset_profiler/configs/config_dev.yml"

    with open(config_file) as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    return conf


class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "dataset_profiler"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: dict = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL},
    }


# Initialize logger
dictConfig(LogConfig().model_dump())

# Load environment variables
load_dotenv()

# Read configuration
app_config = read_configs()
