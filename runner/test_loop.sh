#!/usr/bin/env bash
run_tests() {
    local bugs_found=0
    local compiled_ok=0

    for test_id in $(seq 1 "$NUM_TESTS"); do
        local src="$PROGRAMS_DIR/test_${test_id}.c"
        local harness="$PROGRAMS_DIR/test_${test_id}_harness.c"
        local extras="$PROGRAMS_DIR/test_${test_id}_extras.c"
        local plan_csv="$PROGRAMS_DIR/test_${test_id}_plan.csv"
        local targets_txt="$PROGRAMS_DIR/test_${test_id}_targets.txt"
        local seed=$((SEED_BASE + test_id))
        local max_funcs=$(( (seed % 6) + 5 ))

        if ! timeout "$TIMEOUT_GEN" "$CSMITH_BIN" \
            --seed "$seed" --max-funcs "$max_funcs" \
            --no-safe-math --no-packed-struct > "$src" 2>/dev/null; then
            continue
        fi
        [ -s "$src" ] || continue

        if ! timeout "$TIMEOUT_GEN" python3 "$HARNESS_GEN" \
            "$src" "$harness" "$plan_csv" "$targets_txt" "$seed" \
            "$MIN_TARGET_FUNCS" "$MAX_TARGET_FUNCS"; then
            rm -f "$src" "$harness" "$plan_csv" "$targets_txt"
            continue
        fi

        if ! timeout "$TIMEOUT_GEN" python3 "$EXTRAS_GEN" "$extras" "$seed"; then
            rm -f "$src" "$harness" "$plan_csv" "$targets_txt" "$extras"
            continue
        fi

        local test_had_bug=0
        unset FSTATUS
        declare -A FSTATUS

        for cfg_idx in "${!CONFIG_NAMES[@]}"; do
            local cfg_name="${CONFIG_NAMES[$cfg_idx]}"
            local cfg_cmd="${CONFIG_CMDS[$cfg_idx]}"
            local binary="$PROGRAMS_DIR/test_${test_id}_${cfg_name}"
            local err_log="$LOGS_DIR/err_${test_id}_${cfg_name}.log"

            if ! timeout "$TIMEOUT_COMPILE" bash -lc \
                "$cfg_cmd -I'$CSMITH_DIR/runtime' -I'$CSMITH_DIR/build/runtime' \
                 -o '$binary' '$src' '$harness' '$extras'" \
                >"$err_log" 2>&1; then
                continue
            fi
            compiled_ok=$((compiled_ok + 1))

            local analysis_json="$LOGS_DIR/analysis_${test_id}_${cfg_name}.json"
            if ! python3 "$ANALYZE" \
                --binary "$binary" --plan "$plan_csv" --targets "$targets_txt" \
                --test-id "$test_id" --config "$cfg_name" \
                --out "$analysis_json" >> "$err_log" 2>&1; then
                rm -f "$binary"
                continue
            fi

            python3 "$COLLECT_RESULTS" "$analysis_json" \
                "$RESULTS_DIR/summary.csv" \
                "$RESULTS_DIR/bugs.csv" \
                "$RESULTS_DIR/aliases.csv" \
                "$RESULTS_DIR/endbr64_counts.csv" \
                "$RESULTS_DIR/jumptable.csv" \
                "$RESULTS_DIR/callsite_detail.csv"

            while IFS=$'\t' read -r tag name st; do
                [ "$tag" = "DIFF" ] || continue
                FSTATUS["${name}::${cfg_name}"]="$st"
            done < <(python3 "$EXTRACT_STATUS" "$analysis_json")

            local this_bugs
            this_bugs=$(python3 -c "import json;print(json.load(open('$analysis_json'))['total_bugs'])")
            if [ "$this_bugs" -gt 0 ]; then
                bugs_found=$((bugs_found + this_bugs))
                test_had_bug=1
            fi

            rm -f "$binary"
        done

        if [ -s "$targets_txt" ]; then
            while IFS= read -r name; do
                [ -z "$name" ] && continue
                local statuses="" prev="" diff=0
                for cfg_name in "${CONFIG_NAMES[@]}"; do
                    local s="${FSTATUS[${name}::${cfg_name}]:-NA}"
                    statuses="$statuses,$s"
                    if [ -n "$prev" ] && [ "$s" != "$prev" ] && \
                       [ "$s" != "NA" ] && [ "$prev" != "NA" ]; then
                        diff=1
                    fi
                    prev="$s"
                done
                if [ "$diff" -eq 1 ]; then
                    echo "$test_id,callee,$name$statuses" >> "$RESULTS_DIR/differential.csv"
                fi
            done < "$targets_txt"
        fi

        if [ "$test_had_bug" -eq 1 ]; then
            cp "$src"      "$BUGS_DIR/bug_test_${test_id}.c"
            cp "$harness"  "$BUGS_DIR/bug_test_${test_id}_harness.c"
            cp "$extras"   "$BUGS_DIR/bug_test_${test_id}_extras.c"
            cp "$plan_csv" "$BUGS_DIR/bug_test_${test_id}_plan.csv"
        else
            rm -f "$src" "$harness" "$extras" "$plan_csv" "$targets_txt"
        fi

        if [ $((test_id % 25)) -eq 0 ]; then
            msg "[*] $test_id/$NUM_TESTS | compiled=$compiled_ok | bugs=$bugs_found"
        fi
    done
}
