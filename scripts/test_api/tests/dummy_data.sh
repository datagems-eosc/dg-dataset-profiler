#!/usr/bin/env bash
#
# Profiles tests/assets/dummy_data through the API.
#
# This is the "everything at once" dataset: a CSV, an Excel workbook and several
# file sets (pdfs, txt files, images, notebooks, word docs), plus a
# DatabaseConnection to ds_mathe. It exercises the widest slice of the profiler.
#
# NOTE on the dataset id: dummy_data/specifications.json reuses the same id as
# meteo_era5land (7c4d20a0-...). The CDD profile path is stored in Redis keyed by
# dataset id, so the two would overwrite each other. A distinct id is used here.
set -uo pipefail

SUITE_NAME="dummy_data"
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

SPEC_FILE="${ASSETS_ROOT}/dummy_data/specifications.json"
DATASET_ID="11111111-1111-4111-8111-111111111111"
PROFILE_FILE="${WORK_DIR}/dummy_data-profile.json"

suite_begin

step "Local assets"
assert_local_dataset_path "dummy_data/data"

step "Profiling job"
if ! run_profile_job "$SPEC_FILE" "$DATASET_ID" "$PROFILE_FILE"; then
    warn "Job did not complete; skipping profile content assertions."
    finish_suite
    exit $?
fi

step "Light profile"
assert_jq "$PROFILE_FILE" '.moma_profile_light["@type"] == "sc:Dataset"' \
    "Light profile is an sc:Dataset"
assert_jq "$PROFILE_FILE" '.moma_profile_light.name == "Dummy data."' \
    "Light profile carries the dataset name"
assert_jq "$PROFILE_FILE" '(.moma_profile_light.distribution | length) > 0' \
    "Light profile has distributions"
assert_json_has_name "$PROFILE_FILE" '.moma_profile_light.distribution[].name' \
    "csv_1.csv" "CSV file object is a distribution"
assert_json_has_name "$PROFILE_FILE" '.moma_profile_light.distribution[].name' \
    "ISCO-08 EN Structure and definitions.xlsx" "Excel file object is a distribution"
assert_jq "$PROFILE_FILE" \
    '[.moma_profile_light.distribution[] | select(.["@type"] == "cr:FileSet")] | length > 0' \
    "File sets (pdfs / txt_files / imgs) are distributions"

if [[ "$SKIP_DB_CONNECTORS" != "1" ]]; then
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_light.distribution[] | select(.["@type"] == "dg:DatabaseConnection") | .name] | index("ds_mathe") != null' \
        "ds_mathe database connection is a distribution"
fi

if heavy_checks_enabled; then
    step "Heavy profile"
    assert_jq "$PROFILE_FILE" '(.moma_profile_heavy.recordSet | length) > 0' \
        "Heavy profile has record sets"
    assert_json_has_name "$PROFILE_FILE" '.moma_profile_heavy.recordSet[].name' \
        "csv_1" "csv_1 record set was extracted"
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[] | select(.name == "csv_1") | .field[].name] | index("dv_agency") != null' \
        "csv_1 record set exposes the dv_agency field"
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[] | select(.name == "csv_1") | .field[].name] | index("dv_validations") != null' \
        "csv_1 record set exposes the dv_validations field"
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[] | select(.name == "csv_1") | .field[] | select(.dataType != null)] | length > 0' \
        "csv_1 fields carry data types"

    step "CDD profile"
    assert_jq "$PROFILE_FILE" '(.cdd_profile.path // "") != ""' \
        "Response points at the generated CDD profile"
fi

step "Clean up"
clean_up_job "$LAST_JOB_ID"

finish_suite
