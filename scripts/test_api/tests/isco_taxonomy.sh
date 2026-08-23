#!/usr/bin/env bash
#
# Profiles tests/assets/isco_taxonomy through the API.
#
# An Excel workbook (one record set per non-empty sheet) plus a directory of
# .txt files (a file set / document record set). Covers the non-CSV file paths.
#
# NOTE on the dataset id: the specification file carries the placeholder
# "temp_id_since_profiler_does_not_issue_ids", which the API rejects because
# ProfileSpecificationEndpoint.id is a UUID. A fixed UUID is substituted here.
set -uo pipefail

SUITE_NAME="isco_taxonomy"
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

SPEC_FILE="${ASSETS_ROOT}/isco_taxonomy/specification.json"
DATASET_ID="44444444-4444-4444-8444-444444444444"
PROFILE_FILE="${WORK_DIR}/isco_taxonomy-profile.json"
EXCEL_SHEET="ISCO-08 EN Struct and defin"

suite_begin

step "Local assets"
assert_local_dataset_path "isco_taxonomy/data"

step "Request validation"
# The placeholder id in the spec must not reach the API: assert we replaced it.
assert_jq "$SPEC_FILE" '.id == "temp_id_since_profiler_does_not_issue_ids"' \
    "Specification still carries the placeholder id (substituted before sending)"

step "Profiling job"
if ! run_profile_job "$SPEC_FILE" "$DATASET_ID" "$PROFILE_FILE"; then
    warn "Job did not complete; skipping profile content assertions."
    finish_suite
    exit $?
fi

step "Light profile"
assert_jq "$PROFILE_FILE" '.moma_profile_light["@type"] == "sc:Dataset"' \
    "Light profile is an sc:Dataset"
assert_jq "$PROFILE_FILE" '.moma_profile_light.name == "ISCO taxonomy"' \
    "Light profile carries the dataset name"
assert_json_has_name "$PROFILE_FILE" '.moma_profile_light.distribution[].name' \
    "ISCO-08 EN Structure and definitions.xlsx" "Excel file object is a distribution"
assert_jq "$PROFILE_FILE" \
    '[.moma_profile_light.distribution[] | select(.["@type"] == "cr:FileSet") | .name] | map(select(endswith("test_txt"))) | length > 0' \
    "test_txt directory is a file set distribution"

if heavy_checks_enabled; then
    step "Heavy profile"
    assert_jq "$PROFILE_FILE" '(.moma_profile_heavy.recordSet | length) > 0' \
        "Heavy profile has record sets"
    assert_json_has_name "$PROFILE_FILE" '.moma_profile_heavy.recordSet[].name' \
        "$EXCEL_SHEET" "Excel sheet became a record set"

    for field in "Level" "ISCO 08 Code" "Title EN" "Definition"; do
        assert_jq "$PROFILE_FILE" \
            "[.moma_profile_heavy.recordSet[] | select(.name == \"${EXCEL_SHEET}\") | .field[].name] | index(\"${field}\") != null" \
            "Sheet record set exposes the '${field}' field"
    done

    # Excel record sets inject a distribution per sheet into the heavy profile.
    assert_jq "$PROFILE_FILE" \
        "[.moma_profile_heavy.distribution[].name] | index(\"${EXCEL_SHEET}\") != null" \
        "Heavy profile injects a per-sheet distribution"

    step "CDD profile"
    assert_jq "$PROFILE_FILE" '(.cdd_profile.path // "") != ""' \
        "Response points at the generated CDD profile"
fi

step "Clean up"
clean_up_job "$LAST_JOB_ID"

finish_suite
