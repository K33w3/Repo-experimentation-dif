#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"
HARNESS_GEN="${PROJECT_DIR}/generate_harness.py"

ANALYZE="${PROJECT_DIR}/analyze_binary.py"
COLLECT_RESULTS="${SCRIPT_DIR}/collect_results.py"
EXTRACT_STATUS="${SCRIPT_DIR}/extract_status.py"
WORK_DIR="${CET_WORK_DIR:-${PROJECT_DIR}}"
CSMITH_DIR="${CSMITH_DIR:-${HOME}/cet_csmith/csmith}"
CSMITH_BIN="${CSMITH_DIR}/build/src/csmith"
PROGRAMS_DIR="${WORK_DIR}/programs"
RESULTS_DIR="${WORK_DIR}/results"
BUGS_DIR="${WORK_DIR}/bugs"
LOGS_DIR="${WORK_DIR}/logs"
NUM_TESTS="${2:-500}"
TIMEOUT_COMPILE=60
TIMEOUT_GEN=20
SEED_BASE="${SEED_BASE:-1337}"
MIN_TARGET_FUNCS=2
MAX_TARGET_FUNCS=10
declare -a CONFIG_NAMES=(
    "gcc-branch-baseline"
    "gcc-branch-lto"
    "clang-branch-baseline"
    "clang-branch-thinlto"
    "clang-branch-fulllto"
)

declare -a CONFIG_CMDS=(
    "gcc -O2 -fcf-protection=branch -fno-pie -no-pie"
    "gcc -O2 -fcf-protection=branch -fno-pie -no-pie -flto"
    "clang -O2 -fcf-protection=branch -fuse-ld=lld -fno-pie -no-pie -Wl,--icf=none"
    "clang -O2 -fcf-protection=branch -fuse-ld=lld -fno-pie -no-pie -Wl,--icf=none -flto=thin"
    "clang -O2 -fcf-protection=branch -fuse-ld=lld -fno-pie -no-pie -Wl,--icf=none -flto"
)
