# Status & Error Codes

This page documents the status codes and error messages that may be returned by the Dataset Profiler API.

## HTTP Status Codes

The Dataset Profiler API uses standard HTTP status codes to indicate the success or failure of requests:

| Status Code | Description |
|-------------|-------------|
| 200 | OK - The request was successful |
| 401 | Unauthorized - Authentication is enabled and the JWT token is missing or invalid |
| 403 | Forbidden - The JWT token is valid but the `client_id` claim is not `airflow` |
| 404 | Not Found - The requested resource does not exist |
| 422 | Unprocessable Entity - The request body failed validation (e.g. missing or malformed fields) |
| 500 | Internal Server Error - An error occurred on the server |
| 503 | Service Unavailable - The Ray cluster is currently unavailable; retry shortly |

!!! note "Validation errors"

    Request body validation is handled by FastAPI/Pydantic and returns a `422`
    response with a detailed list of the offending fields, rather than a `400`.

## Job Status Codes

The following status codes are returned by the `/profiler/job_status/{profile_job_id}` endpoint:

| Status | Description |
|--------|-------------|
| SUBMITTING | The job is being submitted to the processing queue |
| STARTING | The job has been accepted and is starting |
| LIGHT_PROFILE_READY | The light profile (basic metadata and distributions) is ready |
| HEAVY_PROFILES_READY | The heavy profile (including record sets) is ready |
| FAILED | The job has failed |

## Runner Status Codes

The following status codes are returned by the `/profiler/runner_status/{profile_job_id}` endpoint:

| Status | Description |
|--------|-------------|
| pending | The job is waiting to be processed |
| in_progress | The job is currently being processed |
| completed | The job has completed successfully |
| failed | The job has failed |
| unknown | The job ID is not recognized |

## Common Error Messages

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "profile_specification", "name"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

This error occurs when the profile specification in the request body is not properly formatted or is missing required fields. FastAPI/Pydantic returns a `422` with a list pinpointing each invalid field.

### 404 Not Found

```json
{
  "detail": "No profile found for the given job ID. Profiling might still be in progress."
}
```

This error occurs when trying to retrieve a profile that doesn't exist or isn't ready yet.

### 500 Internal Server Error

```json
{
  "detail": "An error occurred while processing the dataset"
}
```

This error indicates a server-side issue that prevented the profiling job from completing successfully.

### 503 Service Unavailable

```json
{
  "detail": "Ray cluster is currently unavailable. Please retry shortly."
}
```

This error is returned by `POST /profiler/trigger_profile` and `GET /profiler/runner_status/{profile_job_id}` when the Ray cluster cannot be reached. The API stays up and reconnects to Ray automatically, so retrying the request shortly typically succeeds.

## Troubleshooting


### "No profile found" Error

If you receive a "No profile found" error when trying to retrieve a profile:

1. Check the job status using the `/profiler/job_status/{profile_job_id}` endpoint
2. If the status is not "LIGHT_PROFILE_READY" or "HEAVY_PROFILES_READY", wait for the job to complete
3. If the job status is "FAILED", check the logs for more information

### Invalid Profile Specification

If you receive a `422` validation error:

1. Ensure all required fields are present in the profile specification
2. Check that field values are of the correct type
3. Verify that each entry in `data_connectors` is valid (e.g. a `RawDataPath` connector points to a valid `dataset_id`)

## Logging

For more detailed error information, check the service logs. The logging level can be configured in the service configuration file.

## Support

If you encounter persistent issues that cannot be resolved using this documentation, please contact the DataGEMS support team or open an issue on the [GitHub repository](https://github.com/datagems-eosc/dataset-profiler/issues).
