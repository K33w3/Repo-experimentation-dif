#!/usr/bin/env python3
"""
This is the CLI entry point for the binary analyzer.
"""

import argparse
import csv
import json
from pathlib import Path

from .disassembly import count_total_endbr, disasm
from .oracles import (
    check_callee_endbr,
    check_callsite_notrack,
    check_cf_check,
    observe_jumptable,
)
from .symbols import build_name_index, collect_symbols, find_alias_groups

def parse_plan(plan_path: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with open(plan_path, newline="") as f:
        for r in csv.DictReader(f):
            rows[r["function"]] = r
    return rows

def main() -> None:
    args = _parse_args()

    plan = parse_plan(args.plan)
    targets = [
        t.strip()
        for t in Path(args.targets).read_text().splitlines()
        if t.strip()
    ]

    addr_map = collect_symbols(args.binary)
    d_full = disasm(args.binary)
    name_to_addr = build_name_index(addr_map)
    alias_groups = find_alias_groups(addr_map)

    callee_bugs, target_status, addr_taken, n_callee = check_callee_endbr(
        targets, plan, name_to_addr, addr_map, d_full,
    )

    (
        site_bugs, callsite_records,
        mapped, nocf_exp, nocf_obs, n_site,
    ) = check_callsite_notrack(targets, plan, d_full)

    cfc_bugs = check_cf_check(name_to_addr, d_full)
    jumptable = observe_jumptable(d_full)

    all_bugs = callee_bugs + site_bugs + cfc_bugs
    total_callee_bugs = n_callee + len(cfc_bugs)

    result = {
        "test_id": args.test_id,
        "config": args.config,
        "total_funcs": sum(len(v) for v in addr_map.values()),
        "target_funcs": len(targets),
        "total_endbr64": count_total_endbr(d_full),
        "addr_taken_endbr_sites": addr_taken,
        "callsites_mapped": mapped,
        "callsites_nocf_expected": nocf_exp,
        "callsites_nocf_observed": nocf_obs,
        "callee_bugs": total_callee_bugs,
        "callsite_bugs": n_site,
        "alias_groups": len(alias_groups),
        "aliases": alias_groups,
        "bugs": all_bugs,
        "total_bugs": len(all_bugs),
        "target_status": target_status,
        "callsite_records": callsite_records,
        "jumptable": jumptable,
    }

    Path(args.out).write_text(json.dumps(result))


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Analyse a CET/IBT-instrumented binary against a test plan.",
    )
    ap.add_argument("--binary", required=True, help="Path to the compiled ELF binary")
    ap.add_argument("--plan", required=True, help="CSV test plan from generate_harness")
    ap.add_argument("--targets", required=True, help="Text file listing target function names")
    ap.add_argument("--test-id", required=True, help="Numeric test identifier")
    ap.add_argument("--config", required=True, help="Compiler configuration name")
    ap.add_argument("--out", required=True, help="Output JSON path")
    return ap.parse_args()


if __name__ == "__main__":
    main()
