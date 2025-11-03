# Dataset Profiler

[![Commit activity](https://img.shields.io/github/commit-activity/m/datagems-eosc/dataset-profiler)](https://img.shields.io/github/commit-activity/m/datagems-eosc/dataset-profiler)
[![License](https://img.shields.io/github/license/datagems-eosc/dataset-profiler)](https://img.shields.io/github/license/datagems-eosc/dataset-profiler)

This is the documentation site for the Dataset Profiler service. The service is part of the wider [DataGEMS](https://datagems.eu/) platform.

The Dataset Profiler service is designed to automatically analyze and extract metadata from various types of datasets. It supports multiple data formats including CSV files, Excel spreadsheets, databases, text documents, and PDF files. The service generates comprehensive profiles that describe the structure, content, and characteristics of datasets, making them more discoverable and usable. The service as the project progresses will provide profiling for additional data types and formats.

## Key Features

- **Multi-format Support**: Profiles CSV files, Excel spreadsheets, databases, text documents, and PDF files
- **Distributed Processing**: Uses Ray for distributed computing to handle large datasets efficiently
- **API-driven**: RESTful API for easy integration with other services
- **Metadata Extraction**: Automatically extracts metadata such as column types, data distributions, and sample values
- **Standardized Output**: Produces standardized JSON-LD profiles that follow the [Croissant Metadata Schema](https://mlcommons.org/working-groups/data/croissant/)


## How It Works

The Dataset Profiler service works by:

1. Accepting dataset specifications through its API (non inferred metadata like name, license, etc.)
2. Analyzing the dataset structure and content
3. Generating a "light" profile with basic metadata (distributions information)
4. Optionally generating a "heavy" profile with detailed record set information (file structure, fields, data types)
5. Returning the profile in a standardized JSON-LD format
