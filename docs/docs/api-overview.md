# API Overview

The Dataset Profiler service provides a RESTful API for submitting profiling jobs, checking job status, and retrieving generated profiles. This document provides an overview of the API endpoints, request/response formats, and usage patterns.

## Authentication

The API can be configured to require authentication using JWT tokens. When authentication is enabled (via the `ENABLE_AUTH` environment variable), all API requests must include a valid JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

The token must contain a `client_id` claim with the value `airflow`. See the [Configuration](configuration.md#authentication) section for more details on authentication.

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
  "profile_specification":
    {
      "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
      "cite_as": "",
      "country": "PT",
      "date_published": "24-05-2025",
      "description": "This dataset was extracted from the MathE platform, an online educational platform developed to support mathematics teaching and learning in higher education. It contains 546 student responses to questions on several mathematical topics. Each record corresponds to an individual answer and includes the following features: Student ID, Student Country, Question ID, Type of Answer (correct or incorrect), Question Level (basic or advanced based on the assessment of the contributing professor), Math Topic (broader mathematical area of the question), Math Subtopic, and Question Keywords. The data spans from February 2019 to December 2023.",
      "fields_of_science": [
        "MATHEMATICS"
      ],
      "headline": "Dataset for Assessing Mathematics Learning in Higher Education.",
      "languages": [
        "en"
      ],
      "keywords": [
        "math",
        "student",
        "higher education"
      ],
      "license": "CC0 1.0",
      "name": "Mathematics Learning Assessment",
      "published_url": "https://dados.ipb.pt//dataset.xhtml?persistentId=doi:10.34620/dadosipb/PW3OWY",
      "uploaded_by": "ADMIN",
      "data_connectors": [
        {
            "type": "RawDataPath",
            "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
        }
      ]
    },
  "only_light_profile": false
}
```

!!! warning "Dataset ID Redundancy"

    There is redundancy in the `id` field of the `profile_specification` and the `dataset_id` field of the `RawDataPath` connector.
    This is intentional mainly for local development reasons, but also to allow future flexibility in specifying different dataset IDs in the connectors if needed.

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

| Field | Type | Description                                                         |
|-------|------|---------------------------------------------------------------------|
| id | UUID | Unique identifier for the dataset                                   |
| name | string | Name of the dataset                                                 |
| description | string | Description of the dataset                                          |
| cite_as | string | Citation information                                                |
| license | string | License information                                                 |
| published_url | string | URL where the dataset is published                                  |
| headline | string | Short headline describing the dataset                               |
| keywords | array | List of keywords                                                    |
| fields_of_science | array | List of scientific fields                                           |
| languages | array | List of languages used in the dataset                               |
| country | string | Country code                                                        |
| date_published | string | Publication date                                                    |
| uploaded_by | string | User who uploaded the dataset                                       |
| data_connectors | array | List of data connectors for accessing the dataset (more info below) |

### Data Connectors

Data connectors specify how to access the raw data for profiling. The following connector types are supported:

* RawDataPath: Specifies a path to the raw data files.
* DatabaseConnection: Specifies connection details for a database.

**Example of a list of connectors:**

```json
[
    {
        "type": "RawDataPath",
        "dataset_id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01"
    },
    {
      "type": "DatabaseConnection",
      "database_name": "ds_era5_land"
    }
]
```

* The `dataset_id` field should be the unique identifier of the dataset in the storage system.
* The `database_name` field should be the name of the database to connect to. We do not need any other info to connect to the database since the service has pre-configured access.

## Profile Types

The service generates three types of profiles:

1. **Light Profile**: Basic metadata about the dataset and its distributions (files)
2. **Heavy Profile**: Detailed information about the dataset structure, including record sets and field information
3. **CDD Profile**: Profile used by the Cross-Dataset Discovery service

!!! warning "CDD Profile"

    The CDD profile field is currently empty and will be implemented in future releases.

## Typical API Usage Flow

1. If authentication is enabled, obtain a valid JWT token
2. Submit a profiling job using `POST /profiler/trigger_profile` (with Authorization header if auth is enabled)
3. Poll the job status using `GET /profiler/job_status/{profile_job_id}` (with Authorization header if auth is enabled)
4. Once the status is `LIGHT_PROFILE_READY` or `HEAVY_PROFILES_READY`, retrieve the profile using `GET /profiler/profile/{profile_job_id}` (with Authorization header if auth is enabled)
5. Optionally, clean up resources using `POST /profiler/clean_up` (with Authorization header if auth is enabled)
