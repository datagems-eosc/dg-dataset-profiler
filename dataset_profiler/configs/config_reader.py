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
        config_file = "dataset_profiler/configs/config_prod.yml"

    with open(config_file) as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    return conf

# Load environment variables
load_dotenv()

# Read configuration
app_config = read_configs()
