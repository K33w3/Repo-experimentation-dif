#!/usr/bin/env python3
"""
We just append the analysis JSON to the CSV results. 
"""
import csv
import json
import sys

def main() -> None:
    (json_path, summary_p, bug_p, alias_p,
     endbr_p, jt_p, cs_p) = sys.argv[1:8]

    with open(json_path) as f:
        d = json.load(f)

    tid = d["test_id"]
    cfg = d["config"]

    with open(summary_p, "a", newline="") as f:
        csv.writer(f).writerow([
            tid, cfg, d["total_funcs"], d["target_funcs"],
            d["addr_taken_endbr_sites"],
            d["callsites_mapped"], d["callsites_nocf_expected"],
            d["callsites_nocf_observed"],
            d["callee_bugs"], d["callsite_bugs"], d["alias_groups"],
        ])

    with open(bug_p, "a", newline="") as f:
        w = csv.writer(f)
        for b in d["bugs"]:
            w.writerow([
                tid, cfg, b["category"], b["issue"],
                b.get("target_addr", ""),
                "|".join(b.get("target_symbols", [])),
                b.get("func_attr", ""), b.get("call_mode", ""),
                b.get("weird_attr", ""), b.get("expected", ""),
                b.get("observed", ""), b.get("details", ""),
            ])

    with open(alias_p, "a", newline="") as f:
        w = csv.writer(f)
        for a in d["aliases"]:
            w.writerow([tid, cfg, a["addr"], "|".join(a["symbols"])])

    with open(endbr_p, "a", newline="") as f:
        csv.writer(f).writerow([tid, cfg, d["total_endbr64"]])

    with open(jt_p, "a", newline="") as f:
        jt = d.get("jumptable", {})
        csv.writer(f).writerow([
            tid, cfg,
            jt.get("table_detected", ""),
            jt.get("indirect_jmp_count", ""),
            jt.get("indirect_jmp_notrack", ""),
        ])

    with open(cs_p, "a", newline="") as f:
        w = csv.writer(f)
        for r in d.get("callsite_records", []):
            w.writerow([
                tid, cfg, r["target"], r["expected_notrack"],
                r["mapped"], r["observed_notrack"],
                r.get("callsite_addr", ""),
            ])


if __name__ == "__main__":
    main()
