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
