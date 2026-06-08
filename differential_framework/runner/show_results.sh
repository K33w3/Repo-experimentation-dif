#!/usr/bin/env bash
show_results() {
    [ -f "$RESULTS_DIR/summary.csv" ] || { err "No results. Run first."; exit 1; }

    msg "summary.csv head:"
    head -5 "$RESULTS_DIR/summary.csv"
    msg ""

    msg "bugs.csv:"
    if [ -s "$RESULTS_DIR/bugs.csv" ] && \
       [ "$(wc -l < "$RESULTS_DIR/bugs.csv")" -gt 1 ]; then
        head -25 "$RESULTS_DIR/bugs.csv"
        msg "..."
        msg "Total bug rows: $(( $(wc -l < "$RESULTS_DIR/bugs.csv") - 1 ))"
    else
        msg "(no bugs recorded)"
    fi
    msg ""

    msg "unique bug patterns:"
    if [ "$(wc -l < "$RESULTS_DIR/bugs.csv")" -gt 1 ]; then
        tail -n +2 "$RESULTS_DIR/bugs.csv" | \
            awk -F, '{print $2","$3","$4","$7","$8","$9}' | sort -u
    fi
    msg ""

    msg "aliases.csv (ICF groups):"
    if [ "$(wc -l < "$RESULTS_DIR/aliases.csv")" -gt 1 ]; then
        head -10 "$RESULTS_DIR/aliases.csv"
        msg "Total alias rows: $(( $(wc -l < "$RESULTS_DIR/aliases.csv") - 1 ))"
    else
        msg "(no aliases)"
    fi
}
