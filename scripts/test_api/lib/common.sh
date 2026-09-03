# shellcheck shell=bash
#
# Shared helpers for the curl-based API tests in scripts/test_api.
#
# Source this from a test script:
#
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"
#
# It provides configuration, curl wrappers over the Dataset Profiler API,
# assertions, job monitoring and clean-up.

# ---------------------------------------------------------------------------
# Configuration (override via environment)
# ---------------------------------------------------------------------------

# Base URL of the running API (docker-compose-dev.yml maps api -> host port 8000).
API_URL="${PROFILER_API_URL:-http://localhost:8000}"

# Every endpoint depends on HTTPBearer, so a token must be sent even when
# ENABLE_AUTH=false (in which case its value is never looked at).
#
# With ENABLE_AUTH=true the API decodes the JWT *without verifying the
# signature* and only requires `client_id == "airflow"` (see routes/auth.py), so
# the default below is a well-formed unsigned-payload JWT carrying exactly that.
# It works in both modes; a plain string like "test-token" would 401 under
# ENABLE_AUTH=true ("Not enough segments").
DEFAULT_API_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiJhaXJmbG93Iiwic3ViIjoicHJvZmlsZXItYXBpLXRlc3RzIn0.c2lnbmF0dXJl"
API_TOKEN="${PROFILER_API_TOKEN:-$DEFAULT_API_TOKEN}"

# How long to wait for a job to reach a terminal state, and how often to poll.
# LLM (CTA / data quality) and database profiling jobs are slow, hence the
# generous default.
JOB_TIMEOUT="${PROFILER_JOB_TIMEOUT:-1200}"
POLL_INTERVAL="${PROFILER_POLL_INTERVAL:-5}"

# Repository root and the host-side asset directory holding the specification
# files. tests/ is bind-mounted into the Ray container at /home/ray/app/tests.
TEST_API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${TEST_API_DIR}/../.." && pwd)"
ASSETS_ROOT="${PROFILER_ASSETS_ROOT:-${REPO_ROOT}/tests/assets}"

# Prefix stripped from the RawDataPath dataset_ids found in the specification
# files. The default suits docker-compose-dev.yml, where the Ray worker resolves
# them against DATA_ROOT_PATH=/home/ray/app/tests/assets/ so the API must be sent
# "<name>/data". Set it to "" when the worker's DATA_ROOT_PATH (+ MOUNT_POINT) is
# the repository root instead, so the spec path is sent verbatim.
PATH_STRIP_PREFIX="${PROFILER_PATH_STRIP_PREFIX-tests/assets/}"

# Set to 1 to drop DatabaseConnection connectors from the request bodies (useful
# when the DataGems Postgres/TimescaleDB instances are not reachable).
SKIP_DB_CONNECTORS="${PROFILER_SKIP_DB_CONNECTORS:-0}"

# Set to 1 to request only the light profile (much faster, skips record sets,
# LLM annotation and SQL statistics).
ONLY_LIGHT_PROFILE="${PROFILER_ONLY_LIGHT:-0}"

# Set to 1 to keep the request/response JSON files written during a run.
KEEP_ARTIFACTS="${PROFILER_KEEP_ARTIFACTS:-0}"

# Docker stack lifecycle. When MANAGE_STACK=1 the run brings the dev stack up
# first and tears it down afterwards -- but only if it was not already running,
# so a stack you started by hand is never pulled out from under you.
COMPOSE_FILE="${PROFILER_COMPOSE_FILE:-${REPO_ROOT}/docker-compose-dev.yml}"
MANAGE_STACK="${PROFILER_MANAGE_STACK:-0}"
# Set to 1 to leave the stack running even when this run started it.
KEEP_STACK="${PROFILER_KEEP_STACK:-0}"
# Set to 1 to pass --build to `docker compose up`.
STACK_BUILD="${PROFILER_STACK_BUILD:-0}"
# Seconds to wait for the API and its dependencies to become healthy after boot.
STACK_TIMEOUT="${PROFILER_STACK_TIMEOUT:-300}"
# Set by stack_up: whether this run is the one that started the containers.
STACK_STARTED_BY_US=0

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

if [[ -t 1 ]]; then
    C_RED=$'\033[0;31m'; C_GREEN=$'\033[0;32m'; C_YELLOW=$'\033[0;33m'
    C_BLUE=$'\033[0;34m'; C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
else
    C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_BOLD=""; C_OFF=""
fi

TESTS_RUN=0
TESTS_FAILED=0
SUITE_NAME="${SUITE_NAME:-api}"
SUITE_START_TS=$(date +%s)

info()  { printf '%s\n' "${C_BLUE}·${C_OFF} $*"; }
warn()  { printf '%s\n' "${C_YELLOW}!${C_OFF} $*"; }
step()  { printf '\n%s\n' "${C_BOLD}▸ $*${C_OFF}"; }

pass() {
    TESTS_RUN=$((TESTS_RUN + 1))
    printf '%s\n' "  ${C_GREEN}PASS${C_OFF} $*"
}

fail() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    printf '%s\n' "  ${C_RED}FAIL${C_OFF} $*"
}

# Banner every script prints first: these datasets are profiled with LLM calls
# (column type annotation) and SQL queries against the DataGems databases, both
# of which live on the SCAYLE internal network.
vpn_banner() {
    cat <<'EOF'
============================================================================
 SCAYLE VPN REQUIRED
============================================================================
 These tests profile real datasets end to end. Profiling reaches out to:
   * the SCAYLE LLM gateway (column type annotation, data quality detection)
   * the DataGems Postgres / TimescaleDB instances (DatabaseConnection specs)
 Both are only reachable over the SCAYLE VPN. Connect to the VPN before
 running, otherwise jobs fail or fall back to empty annotations.

 The dev stack must also be up:
   docker compose -f docker-compose-dev.yml up --build -d
============================================================================
EOF
}

# ---------------------------------------------------------------------------
# Working directory for request/response artifacts
# ---------------------------------------------------------------------------

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/profiler-api-test-XXXXXX")"

# Job ids submitted by this script; used by the clean-up trap.
SUBMITTED_JOBS=()

_cleanup() {
    local exit_code=$?
    # Ask the API to release resources for every job we submitted. The endpoint
    # is a placeholder today, but calling it keeps the test honest about the
    # contract and surfaces regressions if it starts doing real work.
    local job_id
    for job_id in "${SUBMITTED_JOBS[@]:-}"; do
        [[ -z "$job_id" ]] && continue
        curl -sS -o /dev/null -X POST "${API_URL}/profiler/clean_up" \
            -H "Authorization: Bearer ${API_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"profile_job_id\": \"${job_id}\"}" \
            --max-time 30 || true
    done

    if [[ "$KEEP_ARTIFACTS" == "1" ]]; then
        printf '%s\n' "Artifacts kept in ${WORK_DIR}"
    else
        rm -rf "$WORK_DIR"
    fi

    # Last, because the clean-up calls above need the API alive.
    stack_down

    exit "$exit_code"
}
trap _cleanup EXIT

# ---------------------------------------------------------------------------
# Docker stack lifecycle
# ---------------------------------------------------------------------------

compose() {
    docker compose -f "$COMPOSE_FILE" "$@"
}

# True when the API answers its readiness probe.
api_is_up() {
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' "${API_URL}/monitoring/ready" --max-time 5 2>/dev/null)" \
        || return 1
    [[ "$code" == "200" ]]
}

# Polls until the API reports all dependencies healthy, or STACK_TIMEOUT elapses.
wait_for_stack() {
    local deadline=$(( $(date +%s) + STACK_TIMEOUT ))
    local start; start=$(date +%s)
    local ready_seen=0 overall

    while (( $(date +%s) < deadline )); do
        if api_is_up; then
            if [[ $ready_seen -eq 0 ]]; then
                printf '    [%4ds] API is answering, waiting for Ray and Redis\n' \
                    "$(( $(date +%s) - start ))"
                ready_seen=1
            fi
            overall="$(curl -sS "${API_URL}/monitoring/health-check" --max-time 10 2>/dev/null \
                | jq -r '.status // "unknown"' 2>/dev/null)"
            if [[ "$overall" == "healthy" ]]; then
                printf '    [%4ds] stack healthy\n' "$(( $(date +%s) - start ))"
                return 0
            fi
        fi
        sleep 3
    done

    warn "Stack did not become healthy within ${STACK_TIMEOUT}s."
    warn "Inspect it with: docker compose -f ${COMPOSE_FILE} logs api ray-head"
    return 1
}

# Brings the dev stack up when MANAGE_STACK=1. A stack that is already serving
# is left untouched (and not torn down at the end).
stack_up() {
    [[ "$MANAGE_STACK" == "1" ]] || return 0
    require_cmds docker

    step "Docker stack: up"
    if api_is_up; then
        info "API already answering at ${API_URL} - leaving the existing stack alone."
        STACK_STARTED_BY_US=0
        return 0
    fi

    local -a up_args=(up -d)
    [[ "$STACK_BUILD" == "1" ]] && up_args+=(--build)
    info "docker compose -f ${COMPOSE_FILE} ${up_args[*]}"
    if ! compose "${up_args[@]}"; then
        fail "docker compose up failed"
        return 1
    fi
    STACK_STARTED_BY_US=1

    wait_for_stack || return 1
    return 0
}

# Tears the stack down, but only when this run started it and the caller did not
# ask to keep it. Called from the EXIT trap, so it also covers Ctrl-C.
stack_down() {
    [[ "$MANAGE_STACK" == "1" ]] || return 0
    if [[ "$STACK_STARTED_BY_US" != "1" ]]; then
        return 0
    fi
    if [[ "$KEEP_STACK" == "1" ]]; then
        printf '\n%s\n' "Stack left running (PROFILER_KEEP_STACK=1 / --keep-up)."
        printf '  stop it with: docker compose -f %s down\n' "$COMPOSE_FILE"
        return 0
    fi

    printf '\n%s\n' "${C_BOLD}▸ Docker stack: down${C_OFF}"
    compose down || warn "docker compose down failed - check for leftover containers."
    STACK_STARTED_BY_US=0
}

require_cmds() {
    local missing=0 cmd
    for cmd in "$@"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            printf '%s\n' "${C_RED}Missing required command: ${cmd}${C_OFF}" >&2
            missing=1
        fi
    done
    [[ $missing -eq 0 ]] || exit 2
}

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

# api_request METHOD PATH [BODY_FILE]
#
# Performs the call and sets:
#   HTTP_STATUS    - numeric status code (000 on a connection failure)
#   RESPONSE_FILE  - path to the file holding the response body
api_request() {
    local method="$1" path="$2" body_file="${3:-}"
    RESPONSE_FILE="${WORK_DIR}/response-$$-${RANDOM}.json"

    local -a args=(
        -sS -o "$RESPONSE_FILE" -w '%{http_code}'
        -X "$method" "${API_URL}${path}"
        -H "Authorization: Bearer ${API_TOKEN}"
        -H "Accept: application/json"
        --max-time 120
    )
    if [[ -n "$body_file" ]]; then
        args+=(-H "Content-Type: application/json" --data-binary "@${body_file}")
    fi

    # On a connection failure curl still prints the (zero) status code and exits
    # non-zero, so the fallback replaces the value instead of appending to it.
    HTTP_STATUS="$(curl "${args[@]}" 2>"${RESPONSE_FILE}.err")" || HTTP_STATUS="000"
}

# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

assert_status() {
    local expected="$1" label="$2"
    if [[ "$HTTP_STATUS" == "$expected" ]]; then
        pass "${label} (HTTP ${HTTP_STATUS})"
    else
        fail "${label}: expected HTTP ${expected}, got ${HTTP_STATUS}"
        printf '       body: %s\n' "$(head -c 400 "$RESPONSE_FILE" 2>/dev/null)"
    fi
}

assert_eq() {
    local expected="$1" actual="$2" label="$3"
    if [[ "$expected" == "$actual" ]]; then
        pass "${label} (= ${actual})"
    else
        fail "${label}: expected '${expected}', got '${actual}'"
    fi
}

# assert_jq FILE JQ_FILTER LABEL
# Passes when the filter evaluates to true.
assert_jq() {
    local file="$1" filter="$2" label="$3"
    local result
    result="$(jq -r "$filter" "$file" 2>/dev/null || echo "jq-error")"
    if [[ "$result" == "true" ]]; then
        pass "$label"
    else
        fail "${label} (filter evaluated to '${result}')"
    fi
}

# assert_json_has_name FILE JQ_ARRAY_FILTER NAME LABEL
# Passes when NAME appears in the array of strings produced by the filter.
assert_json_has_name() {
    local file="$1" filter="$2" needle="$3" label="$4"
    local found
    found="$(jq -r --arg n "$needle" "[${filter}] | index(\$n) != null" "$file" 2>/dev/null || echo "jq-error")"
    if [[ "$found" == "true" ]]; then
        pass "$label"
    else
        fail "${label}: '${needle}' not found. Present: $(jq -c "[${filter}]" "$file" 2>/dev/null | head -c 400)"
    fi
}

# ---------------------------------------------------------------------------
# Request body construction from the dataset specification files
# ---------------------------------------------------------------------------

# build_request SPEC_FILE DATASET_ID OUT_FILE
#
# The specification files under tests/assets are written in the *internal*
# (croissant-ish) shape consumed by DatasetProfile, while the API expects the
# ProfilingRequest schema (snake_case field names). This maps one onto the other.
#
# RawDataPath dataset_ids are also rewritten: the specs store them as
# "tests/assets/<name>/data/", but the Ray worker resolves them against
# DATA_ROOT_PATH (/home/ray/app/tests/assets/), so the API must receive
# "<name>/data".
build_request() {
    local spec_file="$1" dataset_id="$2" out_file="$3"
    local only_light="false"
    [[ "$ONLY_LIGHT_PROFILE" == "1" ]] && only_light="true"
    local skip_db="false"
    [[ "$SKIP_DB_CONNECTORS" == "1" ]] && skip_db="true"

    jq \
        --arg id "$dataset_id" \
        --arg strip "$PATH_STRIP_PREFIX" \
        --argjson light "$only_light" \
        --argjson skip_db "$skip_db" \
        '
        def strip_assets_root:
            (if ($strip != "") and startswith($strip) then .[($strip | length):] else . end)
            | sub("/+$"; "");
        {
          profile_specification: {
            id: $id,
            name: .name,
            description: .description,
            headline: .headline,
            fields_of_science: (.fieldOfScience // []),
            languages: (.inLanguage // []),
            keywords: (.keywords // []),
            country: (.country // ""),
            published_url: (.url // ""),
            doi: (.doi // ""),
            date_published: .datePublished,
            cite_as: (.citeAs // ""),
            license: .license,
            uploaded_by: (.uploadedBy // "ADMIN"),
            data_connectors: [
              (.data_connectors // [])[]
              | select(($skip_db | not) or (.type != "DatabaseConnection"))
              | if .type == "RawDataPath"
                then {type: .type, dataset_id: (.dataset_id | strip_assets_root)}
                else .
                end
            ]
          },
          only_light_profile: $light
        }' "$spec_file" > "$out_file"
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

# Verifies the API answers and reports healthy dependencies. Returns non-zero
# when the API is unreachable so the caller can abort early instead of timing
# out on every job.
check_api_reachable() {
    step "Preflight: API at ${API_URL}"
    api_request GET "/monitoring/ready"
    if [[ "$HTTP_STATUS" != "200" ]]; then
        fail "API not reachable at ${API_URL} (status ${HTTP_STATUS})"
        warn "Start the stack: docker compose -f docker-compose-dev.yml up -d"
        return 1
    fi
    pass "API is ready"

    api_request GET "/monitoring/health-check"
    assert_status 200 "health-check responds"
    local redis ray overall
    redis="$(jq -r '.redis.status // "unknown"' "$RESPONSE_FILE")"
    ray="$(jq -r '.ray.status // "unknown"' "$RESPONSE_FILE")"
    overall="$(jq -r '.status // "unknown"' "$RESPONSE_FILE")"
    assert_eq "healthy" "$redis" "Redis dependency healthy"
    assert_eq "healthy" "$ray" "Ray dependency healthy"
    if [[ "$overall" != "healthy" ]]; then
        warn "Overall health is '${overall}' - jobs will likely fail."
        return 1
    fi
    return 0
}

# assert_local_dataset_path RELATIVE_PATH
# Guards against config drift: the path sent to the API must exist on the host,
# since ./tests is bind-mounted into the Ray container.
assert_local_dataset_path() {
    local rel="$1"
    local local_path="${ASSETS_ROOT}/${rel}"
    if [[ -d "$local_path" ]] && [[ -n "$(ls -A "$local_path" 2>/dev/null)" ]]; then
        pass "Local dataset directory exists and is not empty: tests/assets/${rel}"
    else
        fail "Local dataset directory missing or empty: ${local_path}"
    fi
}

# ---------------------------------------------------------------------------
# Job submission and monitoring
# ---------------------------------------------------------------------------

# Explains the likely cause of a rejected submission. A failure here is never
# about the dataset's contents: the endpoint only validates the body, writes to
# Redis and hands the task to Ray.
diagnose_submit_failure() {
    case "$HTTP_STATUS" in
        401|403)
            warn "Authentication rejected. The API runs with ENABLE_AUTH=true and wants a JWT"
            warn "whose payload has client_id=\"airflow\" (the signature is not verified)."
            warn "Either unset ENABLE_AUTH or pass a suitable PROFILER_API_TOKEN."
            ;;
        422)
            warn "The API rejected the request body. Re-check the specification mapping in"
            warn "build_request() - e.g. a dataset id that is not a UUID."
            ;;
        5*)
            warn "The API errored while submitting - this is a server-side problem, not a"
            warn "dataset one. Look at the traceback:"
            warn "  docker compose -f ${COMPOSE_FILE} logs --tail 50 api"
            warn "Known cause: dependency skew between the API and Ray images. If the log"
            warn "shows a cloudpickle 'Failed to deserialize' / TypedDict error, the two"
            warn "sides disagree on typing_extensions (api installs uv.lock, ray-head keeps"
            warn "the version baked into the rayproject base image)."
            ;;
        000)
            warn "No response at all - is the API still running? ${API_URL}"
            ;;
    esac
}

# submit_profile BODY_FILE -> sets JOB_ID (empty on failure)
#
# Values are returned through globals rather than stdout on purpose: a command
# substitution would run the function in a subshell and lose the pass/fail
# counters it updates.
submit_profile() {
    local body_file="$1"
    JOB_ID=""
    api_request POST "/profiler/trigger_profile" "$body_file"
    assert_status 200 "POST /profiler/trigger_profile accepted"
    if [[ "$HTTP_STATUS" != "200" ]]; then
        diagnose_submit_failure
        return 1
    fi

    JOB_ID="$(jq -r '.job_id // empty' "$RESPONSE_FILE")"
    if [[ "$JOB_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
        pass "Response carries a UUID job_id"
    else
        fail "Response job_id is not a UUID: '${JOB_ID}'"
    fi
    assert_jq "$RESPONSE_FILE" '.status == "Job submitted"' "Response status is 'Job submitted'"

    SUBMITTED_JOBS+=("$JOB_ID")
    [[ -n "$JOB_ID" ]]
}

# monitor_job JOB_ID -> sets JOB_FINAL_STATUS
#
# Polls GET /profiler/job_status until a terminal state is reached, printing
# every status transition with elapsed time so a long run stays observable. The
# Ray runner status is reported alongside it, which distinguishes "still
# computing" from "the Ray task died".
monitor_job() {
    local job_id="$1"
    local deadline=$(( $(date +%s) + JOB_TIMEOUT ))
    local last_status="" status runner elapsed start
    start=$(date +%s)
    JOB_FINAL_STATUS="unknown"

    local -a terminal=("heavy_profile_ready" "failed" "cleaned_up")
    if [[ "$ONLY_LIGHT_PROFILE" == "1" ]]; then
        terminal+=("light_profile_ready")
    fi

    while (( $(date +%s) < deadline )); do
        api_request GET "/profiler/job_status/${job_id}"
        if [[ "$HTTP_STATUS" != "200" ]]; then
            elapsed=$(( $(date +%s) - start ))
            printf '    [%4ds] job_status HTTP %s\n' "$elapsed" "$HTTP_STATUS"
            sleep "$POLL_INTERVAL"
            continue
        fi
        status="$(jq -r '.status // "unknown"' "$RESPONSE_FILE")"

        if [[ "$status" != "$last_status" ]]; then
            elapsed=$(( $(date +%s) - start ))
            api_request GET "/profiler/runner_status/${job_id}"
            runner="$(jq -r '. // "unknown"' "$RESPONSE_FILE" 2>/dev/null)"
            printf '    [%4ds] status=%-20s runner=%s\n' "$elapsed" "$status" "$runner"
            last_status="$status"
        fi

        local t
        for t in "${terminal[@]}"; do
            if [[ "$status" == "$t" ]]; then
                JOB_FINAL_STATUS="$status"
                return 0
            fi
        done

        sleep "$POLL_INTERVAL"
    done

    elapsed=$(( $(date +%s) - start ))
    printf '    [%4ds] timed out waiting for a terminal status (last: %s)\n' \
        "$elapsed" "${last_status:-none}"
    JOB_FINAL_STATUS="timeout"
    return 1
}

# fetch_profile JOB_ID OUT_FILE
fetch_profile() {
    local job_id="$1" out_file="$2"
    api_request GET "/profiler/profile/${job_id}"
    assert_status 200 "GET /profiler/profile returns the profile"
    cp "$RESPONSE_FILE" "$out_file"
}

# assert_cdd_profile_path DATASET_ID
assert_cdd_profile_path() {
    local dataset_id="$1"
    api_request GET "/profiler/cdd_profile_path/${dataset_id}"
    assert_status 200 "GET /profiler/cdd_profile_path responds"
    local path
    path="$(jq -r '.cdd_profile_path // empty' "$RESPONSE_FILE")"
    if [[ -n "$path" && "$path" == *"${dataset_id}.json" ]]; then
        pass "CDD profile path written: ${path}"
    else
        fail "CDD profile path missing or unexpected: '${path}'"
    fi
}

# clean_up_job JOB_ID - explicit clean-up call, asserted (the trap also calls
# it best-effort for jobs whose script aborted early).
clean_up_job() {
    local job_id="$1"
    local body="${WORK_DIR}/cleanup-${job_id}.json"
    printf '{"profile_job_id": "%s"}\n' "$job_id" > "$body"
    api_request POST "/profiler/clean_up" "$body"
    assert_status 200 "POST /profiler/clean_up accepted"
    assert_jq "$RESPONSE_FILE" '.detail == "SUCCESS"' "Clean up reports SUCCESS"
}

# ---------------------------------------------------------------------------
# Suite driver
# ---------------------------------------------------------------------------

# run_profile_job SPEC_FILE DATASET_ID OUT_PROFILE_FILE
#
# Builds the body, submits, monitors to completion, fetches the profile and
# checks the CDD path. Returns non-zero if the job did not produce a profile,
# so dataset scripts can skip their content assertions.
run_profile_job() {
    local spec_file="$1" dataset_id="$2" out_profile="$3"
    local body="${WORK_DIR}/request-$(basename "$(dirname "$spec_file")").json"

    build_request "$spec_file" "$dataset_id" "$body"
    info "Request body: $(jq -c '.profile_specification | {id, name, data_connectors}' "$body")"

    submit_profile "$body" || return 1
    LAST_JOB_ID="$JOB_ID"
    info "Job id: ${JOB_ID}"

    monitor_job "$JOB_ID" || true

    local expected="heavy_profile_ready"
    [[ "$ONLY_LIGHT_PROFILE" == "1" ]] && expected="light_profile_ready"
    assert_eq "$expected" "$JOB_FINAL_STATUS" "Job reached ${expected}"

    if [[ "$JOB_FINAL_STATUS" != "$expected" ]]; then
        return 1
    fi

    fetch_profile "$JOB_ID" "$out_profile"
    if [[ "$ONLY_LIGHT_PROFILE" != "1" ]]; then
        assert_cdd_profile_path "$dataset_id"
    fi
    return 0
}

# True unless the run was restricted to light profiles, in which case the heavy
# profile is deliberately empty and its assertions must be skipped.
heavy_checks_enabled() {
    [[ "$ONLY_LIGHT_PROFILE" != "1" ]]
}

# suite_begin - banner, tool check and preflight. run_all.sh sets
# PROFILER_SKIP_PREFLIGHT=1 because it already did this once for the whole run.
suite_begin() {
    require_cmds curl jq
    if [[ "${PROFILER_SKIP_PREFLIGHT:-0}" == "1" ]]; then
        printf '\n%s\n' "${C_BOLD}══ ${SUITE_NAME} ══${C_OFF}"
        return 0
    fi
    vpn_banner
    printf '\n%s\n' "${C_BOLD}══ ${SUITE_NAME} ══${C_OFF}"
    stack_up || {
        finish_suite
        exit 1
    }
    check_api_reachable || {
        finish_suite
        exit 1
    }
}

# suite_skip REASON - end the suite without running its checks. Exit code 3 is
# what run_all.sh reports as SKIP rather than PASS or FAIL.
suite_skip() {
    warn "$*"
    printf '\n%s\n' "${C_BOLD}── ${SUITE_NAME} skipped ──${C_OFF}"
    exit 3
}

finish_suite() {
    local elapsed=$(( $(date +%s) - SUITE_START_TS ))
    printf '\n%s\n' "${C_BOLD}── ${SUITE_NAME} summary ──${C_OFF}"
    printf '   checks: %d, failed: %d, duration: %ds\n' "$TESTS_RUN" "$TESTS_FAILED" "$elapsed"
    if [[ "$TESTS_FAILED" -eq 0 ]]; then
        printf '%s\n' "   ${C_GREEN}ALL CHECKS PASSED${C_OFF}"
        return 0
    fi
    printf '%s\n' "   ${C_RED}${TESTS_FAILED} CHECK(S) FAILED${C_OFF}"
    return 1
}
