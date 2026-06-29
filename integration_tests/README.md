# API integration tests

These tests exercise the **running** Dataset Profiler HTTP API end to end. Unlike
the unit tests under [`tests/`](../tests), which import `DatasetProfile` directly,
these submit real profiling jobs over HTTP and assert on the returned profiles.

## Prerequisites

Start the dev stack (API + Ray head + Redis):

```bash
docker compose -f docker-compose-dev.yml up --build
```

The API must be reachable at `http://localhost:8000` (override with
`PROFILER_API_URL`). If it is not reachable or its dependencies are unhealthy,
the tests **skip** rather than fail.

## Running

From the repository root:

```bash
pytest integration_tests/
```

They are not picked up by a plain `pytest` run (the default `testpaths` is
`tests`), so they only run when explicitly requested.

> The first job after a cold start can be slow while the Ray worker warms up.
> The per-job timeout is `PROFILER_JOB_TIMEOUT` seconds (default 300).

## How dataset paths are resolved

The API resolves a `RawDataPath` `dataset_id` relative to `DATA_ROOT_PATH`
(`/home/ray/app/tests/assets/` in `docker-compose-dev.yml`, which mounts the
repo's `./tests`). So the `dataset_id` sent to the API is **relative to
`tests/assets/`** — e.g. `zoo_24/data`, not the `tests/assets/zoo_24/data` form
used by the unit-test `specifications.json` files.

[`test_dataset_path_exists_locally`](test_profiling.py) verifies each configured
path corresponds to a real, non-empty directory on the host, guarding against
config drift.

## Configuration

All knobs live in [`config.py`](config.py):

- `BASE_URL` / `PROFILER_API_URL` — API location
- `AUTH_TOKEN` / `PROFILER_API_TOKEN` — bearer token (any value works when
  `ENABLE_AUTH=false`; the endpoints still require the header to be present)
- `DATASETS` — the datasets profiled and their expected files / record sets /
  fields

To add a dataset, append an entry to `DATASETS` with its `data_path` (relative to
`tests/assets/`) and expected outputs.
