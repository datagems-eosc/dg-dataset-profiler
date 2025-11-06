# Configuration

This document describes how to configure the Dataset Profiler service for different environments and use cases.

## Configuration Files

The Dataset Profiler service uses YAML configuration files located in the `dataset_profiler/configs/` directory:

- `config_dev.yml`: Development environment configuration
- `config_prod.yml`: Production environment configuration

The appropriate configuration file is loaded based on the `ENVIRONMENT` environment variable, which can be set to `dev` or `prod`.

## Configuration Structure

The configuration files have the following structure:

```yaml
mode: "dev"  # or "prod"

fastapi:
  workers: 1
  debug: True
  reload: True
  host: '0.0.0.0'
  port: 4557

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  app_name: "dataset-profiler"
  enable_json_format: false
  file_log_path: "./dataset-profiler-dev.log"
```

Note that the production configuration file (`config_prod.yml`) does not have fastapi configuration since the deployed service has these parameters in the `uvicorn` command line found in `Dockerfile.api`:

```yaml
mode: "prod"

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  app_name: "dataset-profiler"
  enable_json_format: true
  file_log_path: "./logs/dataset-profiler-dev.log"
```

## Configuration Options

### FastAPI Configuration

| Option | Description | Default |
|--------|-------------|---------|
| host | Host to bind the API server | 0.0.0.0 |
| port | Port to bind the API server | 4557 |
| debug | Enable debug mode | True (dev) |
| workers | Number of worker processes | 1 |
| reload | Enable auto-reload on code changes | True (dev) |

### Logging Configuration

| Option | Description | Default |
|--------|-------------|---------|
| level | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | INFO |
| app_name | Application name for logging | dataset-profiler |
| enable_json_format | Enable JSON formatted logs | false (dev), true (prod) |
| file_log_path | Path for log file | ./dataset-profiler-dev.log (dev), ./logs/dataset-profiler-dev.log (prod) |

## Environment Variables

Environment variables can be used to override configuration values. The following environment variables are supported based on the `.env.example` file:

| Variable | Description | Default |
|----------|-------------|---------|
| DATAGEMS_POSTGRES_HOST | PostgreSQL database host | host_name |
| DATAGEMS_POSTGRES_PORT | PostgreSQL database port | 5555 |
| DATAGEMS_POSTGRES_USERNAME | PostgreSQL database username | username |
| DATAGEMS_POSTGRES_PASSWORD | PostgreSQL database password | password |
| RAW_DATA_ROOT_PATH | Root path for raw data storage (mount to s3) | '' |
| RAY_ADDRESS | Address of the Ray head node | ray://localhost:10001 |
| REDIS_HOST | Redis host | localhost |
| REDIS_PORT | Redis port | 6379 |
| REDIS_DB | Redis database number | 0 |
