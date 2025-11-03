# API Overview

The Dataset Profiler service provides a RESTful API for submitting profiling jobs, checking job status, and retrieving generated profiles. This document provides an overview of the API endpoints, request/response formats, and usage patterns.

## Base URL

The base URL for all API endpoints regarding profiling is:

```
https://{host}/profiler
```

Where `{host}` is the hostname where the Dataset Profiler service is deployed.

## API Endpoints

### Submit Profiling Job

```
POST /profiler/trigger_profile
```

Submits a new dataset profiling job.

#### Request Body

```json
{
  "profile_specification": {
    "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
    "name": "Mathematics Learning Assessment",
    "description": "Dataset for assessing mathematics learning in higher education",
    "cite_as": "Author et al. (2023)",
    "license": "CC0 1.0",
    "published_url": "https://example.com/dataset",
    "headline": "Dataset for Assessing Mathematics Learning in Higher Education",
    "keywords": ["math", "student", "higher education"],
    "fields_of_science": ["MATHEMATICS"],
    "languages": ["en"],
    "country": "PT",
    "date_published": "24-05-2025",
    "dataset_file_path": "/path/to/dataset/",
    "uploaded_by": "ADMIN"
  },
  "only_light_profile": false
}
```

#### Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "Job submitted"
}
```

### Check Job Status

```
GET /profiler/job_status/{profile_job_id}
```

Checks the detailed status of a profiling job.

#### Response

One of the following status values:
- `SUBMITTING`
- `STARTING`
- `LIGHT_PROFILE_READY`
- `HEAVY_PROFILES_READY`
- `FAILED`


### Check Runner Status

```
GET /profiler/runner_status/{profile_job_id}
```

Checks the status of the Ray task for a given job ID.

#### Response

One of the following status values:
- `pending`
- `in_progress`
- `completed`
- `failed`
- `unknown`

### Retrieve Profile

```
GET /profiler/profile/{profile_job_id}
```

Retrieves the generated profile for a completed job.

#### Response

```json
{
  "moma_profile_light": { ... },
  "moma_profile_heavy": { ... },
  "cdd_profile": { ... }
}
```

### Clean Up Job Resources

```
POST /profiler/clean_up
```

Cleans up resources associated with a completed job.

#### Request Body

```json
{
  "profile_job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Response

```json
{
  "detail": "SUCCESS"
}
```

## Profile Specification

The profile specification object contains metadata about the dataset to be profiled:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier for the dataset |
| name | string | Name of the dataset |
| description | string | Description of the dataset |
| cite_as | string | Citation information |
| license | string | License information |
| published_url | string | URL where the dataset is published |
| headline | string | Short headline describing the dataset |
| keywords | array | List of keywords |
| fields_of_science | array | List of scientific fields |
| languages | array | List of languages used in the dataset |
| country | string | Country code |
| date_published | string | Publication date |
| dataset_file_path | string | Path to the dataset files |
| uploaded_by | string | User who uploaded the dataset |

## Profile Types

The service generates three types of profiles:

1. **Light Profile**: Basic metadata about the dataset and its distributions (files)
2. **Heavy Profile**: Detailed information about the dataset structure, including record sets and field information
3. **CDD Profile**: Profile used by the Cross-Dataset Discovery service

!!! warning "CDD Profile"

    The CDD profile field is currently empty and will be implemented in future releases.

## Typical API Usage Flow

1. Submit a profiling job using `POST /profiler/trigger_profile`
2. Poll the job status using `GET /profiler/job_status/{profile_job_id}`
3. Once the status is `LIGHT_PROFILE_READY` or `HEAVY_PROFILES_READY`, retrieve the profile using `GET /profiler/profile/{profile_job_id}`
4. Optionally, clean up resources using `POST /profiler/clean_up`
