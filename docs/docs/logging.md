# Logging & Accounting

This document describes the logging and monitoring capabilities of the Dataset Profiler service.

## Logging System

The Dataset Profiler service uses a structured logging system based on the Python `structlog` library. Logs are formatted as JSON by default, making them easy to parse and analyze with log management tools.

## Log Configuration

Logging is configured in the `dataset_profiler/configs/config_logging.py` module. The configuration can be customized through environment variables and the configuration file.

### Log Levels

The following log levels are supported:

| Level | Description |
|-------|-------------|
| DEBUG | Detailed information, typically useful only for diagnosing problems |
| INFO | Confirmation that things are working as expected |
| WARNING | Indication that something unexpected happened, but the application is still working |
| ERROR | Due to a more serious problem, the application has not been able to perform a function |
| CRITICAL | A serious error, indicating that the application itself may be unable to continue running |

The default log level is `INFO` in production and `DEBUG` in development.

### Log Formats

Two log formats are supported and selected based on the configuration yaml file:

1. **JSON**: Structured logs in JSON format (default in production)
2. **Text**: Human-readable logs (default in development)

### Log Outputs

Logs can be directed to:

1. **stdout**: Standard output (default)
2. **file**: Log file

## Where logs appear (Kubernetes / Lens)

The service runs across two pods, and profiling work happens on Ray workers, so a
single request produces logs in more than one place:

| Component | Runs in | Logs surface in |
|-----------|---------|-----------------|
| API request handling (`routes`, `ray_client`) | API pod (driver) | `dataset-profiler` (API) pod — Lens **Logs** tab |
| Profiling job (`profile_job` and everything under `profile_components`) | Ray worker process | **Both** the `ray-head` pod (worker stdout) **and** the API pod (forwarded from the worker) |

Two mechanisms make the profiling-job logs visible:

1. **`log_to_driver=True`** (set in `dataset_profiler/job_manager/ray_client.py`)
   forwards Ray worker task logs to the driver, so they also appear in the API
   pod's stdout. Without this, worker logs are written only to Ray's internal
   session log files (`/tmp/ray/session_*/logs/`) and never reach Lens.
2. A **`worker_process_setup_hook`** (`setup_worker_logging` in
   `dataset_profiler/configs/config_logging.py`) configures the same structured
   handlers inside every worker, including a handler that writes to the
   container's stdout (`/proc/1/fd/1`) so the logs also show in the `ray-head`
   pod. As a result a profiling-job line may appear in **both** pods — this
   duplication is intentional and makes debugging robust to either pod being the
   one you happen to be looking at.

## Tracing a single job

`profile_job` binds the `job_id` and `dataset_id` into the `structlog` context
(`bind_contextvars`) at the start of the task, so **every** log line emitted
downstream in the profiling core is automatically tagged with them. To follow one
job end to end, filter the Lens Logs tab (or your log tooling) by its `job_id`.
