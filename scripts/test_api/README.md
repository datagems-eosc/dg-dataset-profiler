# Curl API tests

End-to-end tests that drive the **running** Dataset Profiler HTTP API with
`curl`, profile four sample datasets from `tests/assets/`, and assert on the
profiles that come back.

> **The SCAYLE VPN must be up.** Profiling calls the SCAYLE LLM gateway (column
> type annotation) and the DataGems Postgres/TimescaleDB instances
> (`DatabaseConnection` specifications). Both live on the SCAYLE internal
> network. Without the VPN, the database datasets fail and semantic annotation
> comes back empty. Every script prints this reminder before it starts.

These complement the Python suite in [`integration_tests/`](../../integration_tests):
same idea, but dependency-free (bash + curl + jq) and driven from the dataset
specification files themselves.

## Prerequisites

1. **SCAYLE VPN** connected.
2. The dev stack up — either let the runner handle it (`--stack`, see below) or
   start it yourself:
   ```bash
   docker compose -f docker-compose-dev.yml up --build -d
   ```
   The API must answer on `http://localhost:8000` (override with `PROFILER_API_URL`).
3. `curl` and `jq` on the PATH (plus `docker` if you use `--stack`).

## Running

```bash
# everything (health + all four datasets) against an already-running stack
./scripts/test_api/run_all.sh

# a subset, in the given order
./scripts/test_api/run_all.sh health mathe_assessment

# a single suite standalone (does its own preflight)
./scripts/test_api/tests/mathe_assessment.sh
```

### Letting the script manage the containers

```bash
./scripts/test_api/run_all.sh --stack            # up -> run -> down
./scripts/test_api/run_all.sh --build            # same, but `up --build`
./scripts/test_api/run_all.sh --stack --keep-up  # up -> run, leave it running
./scripts/test_api/run_all.sh --up               # only start it (waits until healthy)
./scripts/test_api/run_all.sh --down             # only stop it
```

With `--stack` the runner starts `docker-compose-dev.yml`, waits until
`/monitoring/health-check` reports Redis **and** Ray healthy (up to
`PROFILER_STACK_TIMEOUT`, ~30 s in practice on a warm image), runs the suites,
and tears the stack down again — including on Ctrl-C or an early abort, via an
`EXIT` trap.

Two safeguards worth knowing:

- **A stack that is already serving is reused and never torn down.** The runner
  only stops containers it started itself, so `--stack` cannot pull the rug out
  from under a stack you are using for something else.
- Individual suites can do the same on their own: `PROFILER_MANAGE_STACK=1
  ./scripts/test_api/tests/mathe_assessment.sh`. Under `run_all.sh` the child
  suites never touch docker — the runner owns the lifecycle.

Without any of these flags nothing docker-related happens; the stack is assumed
to be up.

Each suite prints per-check `PASS`/`FAIL` lines; `run_all.sh` ends with a
per-suite summary table. Exit codes: `0` all checks passed, `1` something
failed, `3` the suite skipped itself as not applicable (reported as `SKIP` by
`run_all.sh`, which still exits `0`).

## Suites

| Suite | Dataset | What it covers | Typical time |
|---|---|---|---|
| `health` | – | liveness, readiness, Redis/Ray health, OpenAPI, 404 paths | seconds |
| `mathe_assessment` | `tests/assets/mathe_assessment` | single CSV: distributions, record set fields, statistics, LLM semantic types | ~1 min |
| `isco_taxonomy` | `tests/assets/isco_taxonomy` | Excel workbook (one record set per sheet) plus a `.txt` file set | ~1 min |
| `dummy_data` | `tests/assets/dummy_data` | the mixed bag: CSV + Excel + pdf/txt/image/notebook file sets + the `ds_mathe` database connection | a few min |
| `meteo_era5land` | `tests/assets/meteo_era5land` | database-only dataset (`ds_era5_land`): schema introspection and per-column statistics SQL | slowest, many minutes |

Suites run fastest-first so a broken stack surfaces quickly.

## Monitoring a run

Profiling is asynchronous. After `POST /profiler/trigger_profile` the scripts
poll `GET /profiler/job_status/{job_id}` every `PROFILER_POLL_INTERVAL` seconds
until a terminal state, printing every status transition with the elapsed time
and the Ray runner status next to it:

```
    [   0s] status=submitting           runner=in_progress
    [  15s] status=light_profile_ready  runner=in_progress
    [ 214s] status=heavy_profile_ready  runner=completed
```

`status` is the profiler's own progress (Redis-backed, authoritative);
`runner` is the Ray task state, which tells a slow job apart from a dead one.
A job that does not reach a terminal state within `PROFILER_JOB_TIMEOUT`
is reported as a timeout and the suite fails.

Live logs while a run is in flight:

```bash
docker compose -f docker-compose-dev.yml logs -f api ray-head
```

## Configuration

All knobs are environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `PROFILER_API_URL` | `http://localhost:8000` | API base URL |
| `PROFILER_API_TOKEN` | `test-token` | Bearer token. The endpoints require the header even when `ENABLE_AUTH=false`, in which case the value is not checked |
| `PROFILER_JOB_TIMEOUT` | `1200` | Seconds to wait for a job to reach a terminal state |
| `PROFILER_POLL_INTERVAL` | `5` | Seconds between status polls |
| `PROFILER_ASSETS_ROOT` | `<repo>/tests/assets` | Where the specification files live |
| `PROFILER_ONLY_LIGHT` | `0` | `1` requests light profiles only — fast, and it needs neither the LLM nor the databases. Heavy assertions are skipped automatically |
| `PROFILER_SKIP_DB_CONNECTORS` | `0` | `1` drops `DatabaseConnection` connectors from the request bodies. Use when the DataGems databases are unreachable; `meteo_era5land` then skips itself |
| `PROFILER_KEEP_ARTIFACTS` | `0` | `1` keeps the request/response JSON files and prints their directory |
| `PROFILER_MANAGE_STACK` | `0` | `1` is the same as `--stack`: start the containers before the run, stop them after |
| `PROFILER_KEEP_STACK` | `0` | `1` is the same as `--keep-up`: leave a stack this run started running |
| `PROFILER_STACK_BUILD` | `0` | `1` adds `--build` to `docker compose up` |
| `PROFILER_STACK_TIMEOUT` | `300` | Seconds to wait for the stack to report healthy after `up` |
| `PROFILER_COMPOSE_FILE` | `<repo>/docker-compose-dev.yml` | Compose file used for the lifecycle commands |

Useful combination for a quick smoke test that works **without** the VPN:

```bash
PROFILER_ONLY_LIGHT=1 PROFILER_SKIP_DB_CONNECTORS=1 ./scripts/test_api/run_all.sh
```

## How the request bodies are built

The bodies are generated from the datasets' own specification files
(`tests/assets/<dataset>/specification[s].json`) by `build_request` in
[`lib/common.sh`](lib/common.sh). Two transformations are needed:

1. **Schema shape.** The asset files are in the internal (croissant-ish) form
   consumed by `DatasetProfile` (`fieldOfScience`, `inLanguage`, `datePublished`,
   `citeAs`, `url`, `uploadedBy`), while the endpoint expects `ProfilingRequest`
   (`fields_of_science`, `languages`, `date_published`, `cite_as`,
   `published_url`, `uploaded_by`). The jq program maps one onto the other.

2. **`RawDataPath` paths.** The specs store `tests/assets/<name>/data/`, but the
   Ray worker resolves a connector's `dataset_id` against `DATA_ROOT_PATH`
   (`/home/ray/app/tests/assets/`, where `./tests` is bind-mounted). So the API
   receives `<name>/data`. Each suite also asserts the corresponding host
   directory exists and is non-empty, which catches config drift.

### Dataset ids

Two specifications cannot be used verbatim, and the suites override them:

- `isco_taxonomy` carries `"temp_id_since_profiler_does_not_issue_ids"`, which
  the API rejects (`ProfileSpecificationEndpoint.id` is a UUID) →
  `44444444-4444-4444-8444-444444444444`.
- `dummy_data` reuses the same UUID as `meteo_era5land`
  (`7c4d20a0-…`). The CDD profile path is stored in Redis keyed by dataset id,
  so the two runs would clobber each other → `11111111-1111-4111-8111-111111111111`.

`mathe_assessment` and `meteo_era5land` use the ids from their own spec files.

## Clean-up

- Every submitted job gets `POST /profiler/clean_up` — asserted at the end of a
  successful suite, and called best-effort by an `EXIT` trap for jobs whose
  script aborted early (including on Ctrl-C).
- The temporary directory holding request/response JSON is removed on exit
  unless `PROFILER_KEEP_ARTIFACTS=1`.
- The docker stack is stopped (`docker compose down`) when the run started it
  and `--keep-up` was not given. A pre-existing stack is left running. Named
  volumes are kept, so Redis data survives a teardown.
- **Not cleaned up, by design:** job statuses and profiles stay in Redis
  (`clean_up` is a placeholder server-side anyway), and the CDD profile JSON
  files written by the Ray worker stay in its working directory. Reruns reuse
  the same dataset ids and simply overwrite them.

## Adding a dataset

1. Copy one of the scripts in [`tests/`](tests) — `mathe_assessment.sh` is the
   simplest template.
2. Point `SPEC_FILE` at the dataset's specification file and set `DATASET_ID`
   (its own id when it is a valid, unique UUID).
3. Replace the assertions with what that dataset should produce.
4. Add the suite name to `ALL_SUITES` in [`run_all.sh`](run_all.sh).
