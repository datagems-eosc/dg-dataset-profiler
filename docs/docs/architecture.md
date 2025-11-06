# Service Architecture

The Dataset Profiler service is designed with a microservice architecture that enables efficient and scalable dataset profiling. This document outlines the key components and their interactions.

## High-Level Architecture

The following diagram illustrates the high-level architecture of the Dataset Profiler service:

![Architecture Diagram](images/dataset_profiler_architecture.png)

## Component Details

### API Layer

The Backend layer is built using FastAPI and provides the endpoints documented in [API Documentation](openapi.md).

Concerning profiling specifically the following endpoints are used:

- `/profiler/trigger_profile`: Submit a new profiling job
- `/profiler/runner_status/{profile_job_id}`: Check the status of the Ray task
- `/profiler/job_status/{profile_job_id}`: Check the status of the profiling job
- `/profiler/profile/{profile_job_id}`: Retrieve the generated profile
- `/profiler/clean_up`: Clean up resources for a completed job

### Job Manager

The Job Manager is responsible for:

- Creating unique job IDs for profiling requests
- Submitting jobs to the Ray cluster
- Tracking job status (submitting, starting, light profile ready, heavy profiles ready)
- Storing and retrieving job results

### Profiling Engine

The Profiling Engine performs the actual dataset analysis and consists of:

- **Dataset Specification Parser**: Parses and validates input specifications
- **Distribution Extractor**: Identifies and extracts metadata about dataset files
- **Record Set Extractor**: Analyzes the structure and content of datasets
- **Profile Generator**: Assembles the extracted information into standardized profiles

### Supported Data Types

The service can profile the following types of data:

- **Tabular Data**: CSV files, Excel spreadsheets
- **Databases**: SQL databases with table structures
- **Documents**: Text files, PDF documents
- **File Collections**: Sets of related files

### Distributed Computing Layer

The service uses Ray for distributed computing, which enables:

- Parallel processing of multiple profiling processes
- Efficient resource utilization
- Fault tolerance and automatic recovery

### Profile Job Cache

The profile job cache handles:

- Job status monitoring
- The generated profiles

Both are stored into Redis and are retrievable through the job ID.

## Data Flow

1. Client submits a profiling request with dataset specifications
2. API validates the request and creates a job
3. Job Manager submits the job to the Ray cluster
4. Profiling Engine extracts distributions (light profile)
5. Light profile is stored and made available
6. If requested, Profiling Engine extracts record sets (heavy profile)
7. Complete profile is stored and made available to the client
