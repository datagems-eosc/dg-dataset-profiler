#!/usr/bin/env bash
#
# API smoke checks: liveness, readiness, dependency health, OpenAPI schema and
# the 404 path of the profile endpoint. Runs in a couple of seconds and tells
# you whether the stack is worth pointing the dataset suites at.
set -uo pipefail

SUITE_NAME="health"
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

suite_begin

step "Liveness"
api_request GET "/"
assert_status 200 "GET / responds"
assert_jq "$RESPONSE_FILE" '.message == "Welcome!"' "Root returns the welcome payload"

step "Readiness"
api_request GET "/monitoring/ready"
assert_status 200 "GET /monitoring/ready responds"
assert_jq "$RESPONSE_FILE" '.status == "ready"' "Service reports ready"

step "Dependencies"
api_request GET "/monitoring/health-check"
assert_status 200 "GET /monitoring/health-check responds"
assert_jq "$RESPONSE_FILE" '.redis.status == "healthy"' "Redis is healthy"
assert_jq "$RESPONSE_FILE" '.ray.status == "healthy"' "Ray is healthy"
assert_jq "$RESPONSE_FILE" '.status == "healthy"' "Overall status is healthy"

step "OpenAPI"
api_request GET "/openapi.json"
assert_status 200 "GET /openapi.json responds"
assert_jq "$RESPONSE_FILE" '.paths | has("/profiler/trigger_profile")' \
    "Schema exposes /profiler/trigger_profile"
assert_jq "$RESPONSE_FILE" '.paths | has("/profiler/job_status/{profile_job_id}")' \
    "Schema exposes /profiler/job_status"

step "Unknown job"
api_request GET "/profiler/profile/00000000-0000-4000-8000-000000000000"
assert_status 404 "GET /profiler/profile for an unknown job returns 404"

step "Unknown dataset CDD path"
api_request GET "/profiler/cdd_profile_path/00000000-0000-4000-8000-000000000000"
assert_status 200 "GET /profiler/cdd_profile_path for an unknown dataset responds"
assert_jq "$RESPONSE_FILE" '.cdd_profile_path == null' "Path is null for an unknown dataset"

finish_suite
