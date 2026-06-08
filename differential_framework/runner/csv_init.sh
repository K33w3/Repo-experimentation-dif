#!/usr/bin/env bash
init_csv_files() {
    local dir="$RESULTS_DIR"

    echo 'test_id,config,total_funcs,target_funcs,addr_taken_endbr_sites,callsites_mapped,callsites_nocf_expected,callsites_nocf_observed,callee_bugs,callsite_bugs,alias_groups' \
        > "${dir}/summary.csv"

    echo 'test_id,config,category,issue,target_addr,target_symbols,func_attr,call_mode,weird_attr,expected,observed,details' \
        > "${dir}/bugs.csv"

    echo 'test_id,config,addr,symbols' \
        > "${dir}/aliases.csv"

    echo 'test_id,category,key,gcc_baseline,gcc_lto,clang_baseline,clang_thinlto,clang_fulllto' \
        > "${dir}/differential.csv"

    echo 'test_id,config,total_endbr64' \
        > "${dir}/endbr64_counts.csv"

    echo 'test_id,config,switch_table_detected,indirect_jmp_count,indirect_jmp_notrack' \
        > "${dir}/jumptable.csv"

    echo 'test_id,config,target,expected_notrack,mapped,observed_notrack,callsite_addr' \
        > "${dir}/callsite_detail.csv"
}
