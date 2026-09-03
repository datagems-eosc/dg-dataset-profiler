#!/usr/bin/env bash
#
# Profiles tests/assets/meteo_era5land through the API.
#
# This dataset has no local files at all: its only connector is a
# DatabaseConnection to the DataGems Postgres database ds_era5_land. Profiling
# it runs schema introspection plus per-column statistics SQL, so it is by far
# the slowest of the four and it hard-requires the SCAYLE VPN.
#
# Credentials/hosts come from the Ray container's .env_ray
# (DATAGEMS_POSTGRES_*), not from the host/port in the specification file.
set -uo pipefail

SUITE_NAME="meteo_era5land"
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

SPEC_FILE="${ASSETS_ROOT}/meteo_era5land/specifications.json"
DATASET_ID="$(jq -r '.id' "$SPEC_FILE")"
PROFILE_FILE="${WORK_DIR}/meteo_era5land-profile.json"

suite_begin

if [[ "$SKIP_DB_CONNECTORS" == "1" ]]; then
    suite_skip "PROFILER_SKIP_DB_CONNECTORS=1 and this dataset is database-only."
fi

step "Specification"
assert_jq "$SPEC_FILE" \
    '[.data_connectors[] | select(.type == "DatabaseConnection") | .database_name] | index("ds_era5_land") != null' \
    "Specification declares the ds_era5_land database connection"

step "Profiling job (database, expect several minutes)"
if ! run_profile_job "$SPEC_FILE" "$DATASET_ID" "$PROFILE_FILE"; then
    # Only blame the database when the job actually ran and failed. A rejected
    # submission is a server-side problem, already reported by the submit
    # diagnostics in lib/common.sh.
    if [[ "${JOB_FINAL_STATUS:-}" == "failed" || "${JOB_FINAL_STATUS:-}" == "timeout" ]]; then
        warn "The job itself failed. For a database-only dataset this usually means the"
        warn "DataGems Postgres host is unreachable - check the SCAYLE VPN - or that"
        warn "DATAGEMS_POSTGRES_* in the Ray container's env file are wrong. Note that"
        warn "the host/port in the specification are NOT used for the connection: they"
        warn "only decorate the distribution's contentUrl."
        warn "  docker compose -f ${COMPOSE_FILE} logs --tail 50 ray-head"
    fi
    finish_suite
    exit $?
fi

step "Light profile"
assert_jq "$PROFILE_FILE" '.moma_profile_light["@type"] == "sc:Dataset"' \
    "Light profile is an sc:Dataset"
assert_jq "$PROFILE_FILE" '.moma_profile_light.name == "Era5land"' \
    "Light profile carries the dataset name"
assert_jq "$PROFILE_FILE" \
    '[.moma_profile_light.distribution[] | select(.["@type"] == "dg:DatabaseConnection") | .name] | index("ds_era5_land") != null' \
    "Database connection is a distribution"
assert_jq "$PROFILE_FILE" \
    '[.moma_profile_light.distribution[] | select(.["@type"] == "dg:DatabaseConnection") | .contentUrl // ""] | map(select(startswith("postgresql://"))) | length > 0' \
    "Database distribution exposes a postgresql:// content URL"
assert_jq "$PROFILE_FILE" \
    '[.moma_profile_light.distribution[] | select(.containedIn != null)] | length > 0' \
    "Database tables are listed as distributions contained in the connection"

if heavy_checks_enabled; then
    step "Heavy profile"
    assert_jq "$PROFILE_FILE" '(.moma_profile_heavy.recordSet | length) > 0' \
        "Heavy profile has one record set per database table"
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[] | select((.field | length) > 0)] | length > 0' \
        "Table record sets expose fields"
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[].field[] | select((.statistics // {}) != {})] | length > 0' \
        "Column statistics were computed by SQL"

    step "CDD profile"
    assert_jq "$PROFILE_FILE" '(.cdd_profile.path // "") != ""' \
        "Response points at the generated CDD profile"
fi

step "Clean up"
clean_up_job "$LAST_JOB_ID"

finish_suite
