#!/usr/bin/env bash
#
# Profiles tests/assets/mathe_assessment through the API.
#
# A single ~1 MB CSV. This is the fastest full (light + heavy) run and the best
# smoke test: it still goes through column type annotation, which calls the
# SCAYLE LLM, so it also proves the VPN path works.
set -uo pipefail

SUITE_NAME="mathe_assessment"
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

SPEC_FILE="${ASSETS_ROOT}/mathe_assessment/specifications.json"
# The specification's own id is a valid, unique UUID, so it is used as-is.
DATASET_ID="$(jq -r '.id' "$SPEC_FILE")"
PROFILE_FILE="${WORK_DIR}/mathe_assessment-profile.json"

suite_begin

step "Local assets"
assert_local_dataset_path "mathe_assessment/data"

step "Profiling job"
if ! run_profile_job "$SPEC_FILE" "$DATASET_ID" "$PROFILE_FILE"; then
    warn "Job did not complete; skipping profile content assertions."
    finish_suite
    exit $?
fi

step "Light profile"
assert_jq "$PROFILE_FILE" '.moma_profile_light["@type"] == "sc:Dataset"' \
    "Light profile is an sc:Dataset"
assert_jq "$PROFILE_FILE" '.moma_profile_light.name == "Mathematics Learning Assessment"' \
    "Light profile carries the dataset name"
assert_jq "$PROFILE_FILE" '(.moma_profile_light.keywords | index("math")) != null' \
    "Light profile keeps the submitted keywords"
assert_json_has_name "$PROFILE_FILE" '.moma_profile_light.distribution[].name' \
    "mathe_assessment_dataset.csv" "CSV file object is a distribution"
assert_jq "$PROFILE_FILE" \
    '[.moma_profile_light.distribution[] | select(.name == "mathe_assessment_dataset.csv") | .encodingFormat] | index("text/csv") != null' \
    "CSV distribution is typed as text/csv"

if heavy_checks_enabled; then
    step "Heavy profile"
    assert_json_has_name "$PROFILE_FILE" '.moma_profile_heavy.recordSet[].name' \
        "mathe_assessment_dataset" "mathe_assessment_dataset record set was extracted"

    for field in "Student ID" "Student Country" "Question ID" "Type of Answer" "Question Level"; do
        assert_jq "$PROFILE_FILE" \
            "[.moma_profile_heavy.recordSet[] | select(.name == \"mathe_assessment_dataset\") | .field[].name] | index(\"${field}\") != null" \
            "Record set exposes the '${field}' field"
    done

    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[] | select(.name == "mathe_assessment_dataset") | .field[] | select((.dataType // "") != "")] | length > 0' \
        "Fields carry data types"
    assert_jq "$PROFILE_FILE" \
        '[.moma_profile_heavy.recordSet[] | select(.name == "mathe_assessment_dataset") | .examples] | length > 0' \
        "Record set carries examples"

    # Column type annotation is an LLM call; it degrades to empty on failure rather
    # than breaking the profile, so a miss is reported as a warning, not a failure.
    step "Semantic annotation (LLM, requires VPN)"
    semantic_count="$(jq '[.moma_profile_heavy.recordSet[] | select(.name == "mathe_assessment_dataset") | .field[] | select((.semanticType // "") != "")] | length' "$PROFILE_FILE" 2>/dev/null || echo 0)"
    if [[ "$semantic_count" -gt 0 ]]; then
        pass "Column type annotation produced ${semantic_count} semantic type(s)"
    else
        warn "No semantic types found - check the SCAYLE VPN / LLM configuration (not counted as a failure)"
    fi

    step "CDD profile"
    assert_jq "$PROFILE_FILE" '(.cdd_profile.path // "") != ""' \
        "Response points at the generated CDD profile"
fi

step "Clean up"
clean_up_job "$LAST_JOB_ID"

finish_suite
