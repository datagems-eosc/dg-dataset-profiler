import logging
import structlog
import os

from structlog.types import EventDict, Processor

from dataset_profiler.configs.config_reader import app_config


LOG_SETTINGS = {
    "LOG_LEVEL": app_config["logging"]["level"],
    "LOG_JSON_FORMAT": app_config["logging"]["enable_json_format"],
    "LOG_NAME": app_config["logging"]["app_name"],
    "LOG_ACCESS_NAME": app_config["logging"]["app_name"] + ".access_logs",
    "FILE_LOG_PATH": app_config["logging"]["file_log_path"],
}


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """
    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it. This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging(json_logs: bool = False, log_level: str = "INFO"):
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    log_renderer: structlog.types.Processor
    if json_logs:
        log_renderer = structlog.processors.JSONRenderer()
    else:
        log_renderer = structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    if LOG_SETTINGS["FILE_LOG_PATH"] is not None:
        log_dir = LOG_SETTINGS["FILE_LOG_PATH"].split("/")[:-1]
        if len(log_dir) > 0:
            os.makedirs("/".join(log_dir), exist_ok=True)
        file_handler = logging.FileHandler(LOG_SETTINGS["FILE_LOG_PATH"], mode="a")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


    for _log in ["uvicorn", "uvicorn.error"]:
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


setup_logging(json_logs=LOG_SETTINGS["LOG_JSON_FORMAT"], log_level=LOG_SETTINGS["LOG_LEVEL"])
logger = structlog.stdlib.get_logger(LOG_SETTINGS["LOG_ACCESS_NAME"])
