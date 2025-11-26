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
| ENABLE_AUTH | Enable API authentication | false |

## Authentication

The Dataset Profiler service supports token-based authentication for all API endpoints. Authentication can be enabled or disabled using the `ENABLE_AUTH` environment variable.

When authentication is enabled, all API requests must include a valid JWT token in the Authorization header using the Bearer scheme:

```
Authorization: Bearer <token>
```

The token is expected to be a JWT with the following claims:
- `client_id`: Must be set to 'airflow' for authentication to succeed

Example token payload:
```json
{
  "exp": 1762422572,
  "iat": 1762422272,
  "jti": "trrtcc:208939ba-d97e-4271-af20-d7c3310456b2",
  "iss": "https://datagems-dev.scayle.es/oauth/realms/dev",
  "aud": "account",
  "sub": "a35281e0-641e-41d9-b3ee-b94bf11d866f",
  "typ": "Bearer",
  "azp": "airflow",
  "acr": "1",
  "allowed-origins": [
    "http://localhost:8088"
  ],
  "realm_access": {
    "roles": [
      "default-roles-dev",
      "offline_access",
      "uma_authorization"
    ]
  },
  "resource_access": {
    "account": {
      "roles": [
        "manage-account",
        "manage-account-links",
        "view-profile"
      ]
    }
  },
  "scope": "profile email",
  "clientHost": "172.16.59.4",
  "email_verified": false,
  "preferred_username": "service-account-airflow",
  "clientAddress": "172.16.59.4",
  "client_id": "airflow"
}
```

When authentication is disabled (`ENABLE_AUTH=false`), API endpoints can be accessed without providing a token.
