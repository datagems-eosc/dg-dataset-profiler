#!/usr/bin/env bash
#
# Runs the curl-based API test suites against the stack from docker-compose-dev.yml.
#
#   ./scripts/test_api/run_all.sh                     # everything, stack must be up
#   ./scripts/test_api/run_all.sh mathe_assessment    # selected suites only
#   ./scripts/test_api/run_all.sh --stack             # start the stack, run, tear it down
#   ./scripts/test_api/run_all.sh --up                # only start the stack, then exit
#   ./scripts/test_api/run_all.sh --down              # only tear the stack down
#
# See README.md for the environment variables that tune it.
set -uo pipefail

SUITE_NAME="run_all"
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Ordered fastest-first so a broken stack surfaces quickly. meteo_era5land is
# last: it profiles a remote database and is the slowest by a wide margin.
ALL_SUITES=(health mathe_assessment isco_taxonomy dummy_data meteo_era5land)

usage() {
    cat <<EOF
Usage: run_all.sh [options] [suite ...]

Suites: ${ALL_SUITES[*]}   (default: all, in that order)

Options:
  --stack      Start the dev stack before running and tear it down afterwards.
               A stack that is already up is reused and left running.
  --build      Like --stack, but passes --build to docker compose up.
  --keep-up    With --stack/--build: leave the stack running when done.
  --up         Start the stack (and wait until healthy), then exit.
  --down       Tear the stack down, then exit.
  --no-stack   Never touch docker (default; overrides PROFILER_MANAGE_STACK).
  -h, --help   Show this help.
EOF
}

ACTION="run"
SUITES=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stack)    MANAGE_STACK=1 ;;
        --build)    MANAGE_STACK=1; STACK_BUILD=1 ;;
        --keep-up)  KEEP_STACK=1 ;;
        --up)       MANAGE_STACK=1; KEEP_STACK=1; ACTION="up" ;;
        --down)     ACTION="down" ;;
        --no-stack) MANAGE_STACK=0 ;;
        -h|--help)  usage; exit 0 ;;
        -*)         printf 'Unknown option: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
        *)          SUITES+=("$1") ;;
    esac
    shift
done
[[ ${#SUITES[@]} -eq 0 ]] && SUITES=("${ALL_SUITES[@]}")

# --down: tear down whatever is running and stop. Nothing else to do.
if [[ "$ACTION" == "down" ]]; then
    require_cmds docker
    printf '%s\n' "${C_BOLD}▸ Docker stack: down${C_OFF}"
    compose down
    exit $?
fi

vpn_banner
require_cmds curl jq

printf '\n%s\n' "${C_BOLD}Configuration${C_OFF}"
printf '  API URL            : %s\n' "$API_URL"
printf '  job timeout        : %ss (poll every %ss)\n' "$JOB_TIMEOUT" "$POLL_INTERVAL"
printf '  assets root        : %s\n' "$ASSETS_ROOT"
printf '  only light profile : %s\n' "$ONLY_LIGHT_PROFILE"
printf '  skip DB connectors : %s\n' "$SKIP_DB_CONNECTORS"
printf '  manage stack       : %s (keep up: %s)\n' "$MANAGE_STACK" "$KEEP_STACK"
printf '  suites             : %s\n' "${SUITES[*]}"

# Brings the stack up when asked; the EXIT trap in lib/common.sh takes it back
# down afterwards (unless it was already running, or --keep-up was given).
if ! stack_up; then
    printf '\n%s\n' "${C_RED}Aborting: could not bring the stack up.${C_OFF}"
    exit 1
fi

if [[ "$ACTION" == "up" ]]; then
    printf '\n%s\n' "Stack is up at ${API_URL}."
    printf '  run the tests with: %s\n' "$0"
    printf '  stop it with:       %s --down\n' "$0"
    exit 0
fi

if ! check_api_reachable; then
    printf '\n%s\n' "${C_RED}Aborting: the API is not usable.${C_OFF}"
    exit 1
fi

# The per-suite scripts must not repeat the banner and preflight, and must not
# manage the stack: this run owns its lifecycle.
export PROFILER_SKIP_PREFLIGHT=1
export PROFILER_MANAGE_STACK=0

declare -a RESULT_NAMES=() RESULT_STATUS=() RESULT_TIME=()
overall_rc=0

for suite in "${SUITES[@]}"; do
    script="${TEST_API_DIR}/tests/${suite}.sh"
    if [[ ! -f "$script" ]]; then
        printf '\n%s\n' "${C_RED}Unknown suite: ${suite}${C_OFF}"
        printf '  available: %s\n' "${ALL_SUITES[*]}"
        overall_rc=1
        continue
    fi

    start=$(date +%s)
    bash "$script"
    rc=$?
    duration=$(( $(date +%s) - start ))

    RESULT_NAMES+=("$suite")
    RESULT_TIME+=("$duration")
    case $rc in
        0) RESULT_STATUS+=("PASS") ;;
        3) RESULT_STATUS+=("SKIP") ;;  # suite_skip: not applicable in this configuration
        *) RESULT_STATUS+=("FAIL"); overall_rc=1 ;;
    esac
done

printf '\n%s\n' "${C_BOLD}════════════════════ RUN SUMMARY ════════════════════${C_OFF}"
for i in "${!RESULT_NAMES[@]}"; do
    case "${RESULT_STATUS[$i]}" in
        PASS) colour="$C_GREEN" ;;
        SKIP) colour="$C_YELLOW" ;;
        *)    colour="$C_RED" ;;
    esac
    printf '  %s%-4s%s  %-20s %4ss\n' \
        "$colour" "${RESULT_STATUS[$i]}" "$C_OFF" "${RESULT_NAMES[$i]}" "${RESULT_TIME[$i]}"
done

total=$(( $(date +%s) - SUITE_START_TS ))
printf '  total: %ss\n' "$total"

# Tear the stack down here rather than leaving it to the EXIT trap, so its
# output does not scroll the verdict below off the screen. The trap still
# handles the Ctrl-C / early-abort paths (this call makes it a no-op).
stack_down

if [[ $overall_rc -eq 0 ]]; then
    printf '%s\n' "  ${C_GREEN}ALL SUITES PASSED${C_OFF}"
else
    printf '%s\n' "  ${C_RED}SOME SUITES FAILED${C_OFF}"
fi

exit $overall_rc
