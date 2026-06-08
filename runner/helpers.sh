#!/usr/bin/env bash
msg()  { printf '%s\n' "$*"; }
err()  { printf '[!] %s\n' "$*" >&2; }
need() { command -v "$1" >/dev/null 2>&1; }

require_tools() {
    local missing=0

    for c in python3 nm objdump readelf timeout gcc clang; do
        need "$c" || { err "Missing: $c"; missing=1; }
    done

    if ! need ld.lld && ! need lld; then
        err "Missing: ld.lld (required by Clang configs)"
        err "  Install: sudo apt install lld"
        missing=1
    fi

    if [ ! -x "$CSMITH_BIN" ]; then
        err "CSmith not found at $CSMITH_BIN"
        err "  Set CSMITH_DIR env var or install CSmith first"
        missing=1
    fi

    for f in "$HARNESS_GEN" "$ANALYZE"; do
        if [ ! -f "$f" ]; then
            err "Helper script not found: $f"
            missing=1
        fi
    done

    [ "$missing" -ne 0 ] && exit 1
}

prepare_workdir() {
    mkdir -p "$PROGRAMS_DIR" "$RESULTS_DIR" "$BUGS_DIR" "$LOGS_DIR"
}
