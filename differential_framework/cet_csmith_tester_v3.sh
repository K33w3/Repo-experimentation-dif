#!/usr/bin/env bash
set -u -o pipefail

RUNNER_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/runner" >/dev/null 2>&1 && pwd )"

source "${RUNNER_DIR}/config.sh"
source "${RUNNER_DIR}/helpers.sh"
source "${RUNNER_DIR}/csv_init.sh"
source "${RUNNER_DIR}/test_loop.sh"
source "${RUNNER_DIR}/show_results.sh"

do_run() {
    require_tools
    prepare_workdir
    init_csv_files
    run_tests
}

case "${1:-}" in
    run)     do_run ;;
    results) show_results ;;
    *)
        echo "Usage: $0 {run [N]|results}"
        echo ""
        echo "Environment variables:"
        echo "  CSMITH_DIR    path to CSmith source (default: ~/cet_csmith/csmith)"
        echo "  CET_WORK_DIR  where to put outputs  (default: ~/cet_csmith_v3)"
        echo "  SEED_BASE     starting seed          (default: 1337)"
        echo ""
        echo "Helper scripts resolved from: ${RUNNER_DIR}/"
        exit 1
        ;;
esac
