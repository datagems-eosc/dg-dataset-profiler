# FAQ

This document provides answers to frequently asked questions and information about known issues with the Dataset Profiler service.

## Frequently Asked Questions

### General Questions

#### What is the Dataset Profiler service?

The Dataset Profiler service is a tool that automatically analyzes datasets and generates comprehensive profiles that describe their structure, content, and characteristics. These profiles make datasets more discoverable and usable by providing standardized metadata.

#### What types of datasets can be profiled?

The service can profile the following types of data:
- CSV files
- Excel spreadsheets
- SQL databases
- Text documents
- PDF documents

#### How long does profiling take?

Profiling time depends on the size and complexity of the dataset. Small datasets (< 50MB) typically take a few seconds to a minute. Larger datasets can take several minutes or longer. The service provides status endpoints to check the progress of profiling jobs.


### Technical Questions

#### How do I submit a profiling job?

You can submit a profiling job using the API:

```bash
curl -X POST "https://{host}/profiler/trigger_profile" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_specification": {
      "id": "8930240b-a0e8-46e7-ace8-aab2b42fcc01",
      "name": "Example Dataset",
      "dataset_file_path": "/path/to/dataset/",
      ...
    },
    "only_light_profile": false
  }'
```

For more details, see the [API Overview](api-overview.md) documentation.

#### What's the difference between a light profile and a heavy profile?

- **Light Profile**: Basic metadata about the dataset and its distributions (files)
- **Heavy Profile**: Detailed information about the dataset structure, including record sets and field information

You can request only a light profile by setting `only_light_profile: true` in your request.

#### How can I monitor the status of a profiling job?

You can check the status of a profiling job using the API:

```bash
curl -X GET "https://{host}/profiler/job_status/{profile_job_id}"
```
