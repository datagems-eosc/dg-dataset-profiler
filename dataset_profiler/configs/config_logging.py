import logging
import sys

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


def _same_stream(a, b) -> bool:
    """Return True if two open file objects point to the same underlying file.

    Used to detect when ``/proc/1/fd/1`` is the very same stream as ``sys.stdout``
    (i.e. this process is PID 1, as in the API container) so we don't attach a
    duplicate handler and log every line twice.
    """
    try:
        sa = os.fstat(a.fileno())
        sb = os.fstat(b.fileno())
    except (OSError, ValueError, AttributeError):
        return False
    return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)


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

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    # Clear any handlers from a previous call so re-running setup (e.g. the Ray
    # worker_process_setup_hook firing after the import-time call) does not stack
    # duplicate handlers and emit every line multiple times.
    root_logger.handlers.clear()
    # --- HANDLER 1: For the Ray Dashboard (Intercepted by Ray) ---
    ray_handler = logging.StreamHandler(sys.stdout)
    ray_handler.setFormatter(formatter)
    root_logger.addHandler(ray_handler)

    # --- HANDLER 2: For Kubernetes `kubectl logs` (Bypasses Ray) ---
    # Ray redirects a worker process's own stdout into its session log files, so
    # a worker needs this extra handler writing straight to the container's PID 1
    # stdout to surface in the ray-head pod's logs. In the API/driver container,
    # however, the Python process *is* PID 1, so /proc/1/fd/1 and sys.stdout are
    # the same stream -- adding both handlers there prints every line twice. Only
    # attach this handler when it resolves to a *different* file than stdout.
    try:
        container_stdout = open("/proc/1/fd/1", "w")
        if not _same_stream(container_stdout, sys.stdout):
            k8s_handler = logging.StreamHandler(container_stdout)
            k8s_handler.setFormatter(formatter)
            root_logger.addHandler(k8s_handler)
        else:
            container_stdout.close()
    except (PermissionError, FileNotFoundError, OSError):
        # If we aren't in a container or lack permissions, we safely ignore this.
        # We already have the ray_handler attached, so logs won't be lost.
        pass

    # --- HANDLER 3: Your existing file handler ---
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


def setup_worker_logging() -> None:
    """Configure structured logging inside a Ray worker process.

    Passed to Ray as ``runtime_env["worker_process_setup_hook"]`` so every worker
    that runs a profiling task attaches the same handlers as the driver. This
    makes profiling-job logs structured and lands them on both the ray-head pod
    (via the container-stdout handler) and, together with ``log_to_driver=True``,
    the API pod. ``setup_logging`` clears existing handlers first, so calling this
    after the import-time setup below is idempotent.
    """
    setup_logging(
        json_logs=LOG_SETTINGS["LOG_JSON_FORMAT"],
        log_level=LOG_SETTINGS["LOG_LEVEL"],
    )


setup_logging(json_logs=LOG_SETTINGS["LOG_JSON_FORMAT"], log_level=LOG_SETTINGS["LOG_LEVEL"])
logger = structlog.stdlib.get_logger(LOG_SETTINGS["LOG_ACCESS_NAME"])
