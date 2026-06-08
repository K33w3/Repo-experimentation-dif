#!/usr/bin/env python3
"""
Verification oracles: each oracle inspects a specific aspect of the binary and returns the findings in a structured manner.
"""

from .disassembly import (
    callsite_has_notrack,
    extract_function_body,
    find_indirect_calls,
    function_starts_with_endbr,
)


def check_callee_endbr(
    targets: list[str],
    plan: dict,
    name_to_addr: dict[str, int],
    addr_map: dict[int, list[tuple[str, str, int]]],
    d_text: str,
) -> tuple[list[dict], list[dict], int, int]:
    bugs: list[dict] = []
    target_status: list[dict] = []
    addr_taken_endbr_sites = 0
    callee_bugs = 0
    addr_checked: set[int] = set()

    for name in targets:
        p = plan.get(name)
        if p is None:
            target_status.append({"name": name, "status": "NOPLAN"})
            continue

        addr = name_to_addr.get(name)
        if addr is None:
            target_status.append({"name": name, "status": "ABSENT"})
            continue

        aliases_at_addr = [s[0] for s in addr_map[addr]]
        has_endbr = function_starts_with_endbr(d_text, addr)

        if has_endbr is None:
            target_status.append({"name": name, "status": "UNREADABLE"})
            continue

        target_status.append({
            "name": name,
            "status": "PRESENT" if has_endbr else "MISSING",
        })

        if has_endbr:
            addr_taken_endbr_sites += 1

        if addr in addr_checked:
            continue
        addr_checked.add(addr)

        expected = p["expected_endbr"]
        if expected == "NO" and has_endbr:
            bugs.append(_callee_bug(
                "UNEXPECTED_ENDBR", addr, aliases_at_addr, p,
                "nocf_check function has endbr64 at entry",
            ))
            callee_bugs += 1
        elif expected == "YES" and not has_endbr:
            bugs.append(_callee_bug(
                "MISSING_ENDBR", addr, aliases_at_addr, p,
                "address-taken function lacks endbr64",
            ))
            callee_bugs += 1

    return bugs, target_status, addr_taken_endbr_sites, callee_bugs

def check_callsite_notrack(
    targets: list[str],
    plan: dict,
    d_text: str,
) -> tuple[list[dict], list[dict], int, int, int, int]:
    bugs: list[dict] = []
    callsite_records: list[dict] = []
    callsites_mapped = 0
    callsites_nocf_expected = 0
    callsites_nocf_observed = 0
    callsite_bugs = 0

    for name in targets:
        p = plan.get(name)
        if p is None:
            continue

        shim_name = f"ibt_callsite_{name}"
        body = extract_function_body(d_text, shim_name)
        expect_notrack = p["call_mode"] == "nocf_ptr"

        if expect_notrack:
            callsites_nocf_expected += 1

        if body is None or not find_indirect_calls(body):
            callsite_records.append(_unmapped_record(name, expect_notrack))
            continue

        indirects = find_indirect_calls(body)
        csite_addr, csite_bytes, csite_mnem = indirects[0]
        has_notrack = callsite_has_notrack(csite_bytes, csite_mnem)

        callsites_mapped += 1
        if has_notrack:
            callsites_nocf_observed += 1

        callsite_records.append({
            "target": name,
            "expected_notrack": expect_notrack,
            "mapped": True,
            "observed_notrack": has_notrack,
            "callsite_addr": f"0x{csite_addr}",
        })

        if expect_notrack and not has_notrack:
            bugs.append(_callsite_bug(
                "MISSING_NOTRACK", csite_addr, shim_name, p, csite_mnem,
                csite_bytes,
                f"nocf_check fp call lacks notrack prefix (bytes={csite_bytes})",
            ))
            callsite_bugs += 1
        elif not expect_notrack and has_notrack:
            bugs.append(_callsite_bug(
                "UNEXPECTED_NOTRACK", csite_addr, shim_name, p, csite_mnem,
                csite_bytes,
                f"plain fp call has notrack prefix (bytes={csite_bytes})",
            ))
            callsite_bugs += 1

    return (
        bugs, callsite_records, callsites_mapped,
        callsites_nocf_expected, callsites_nocf_observed, callsite_bugs,
    )

def check_cf_check(
    name_to_addr: dict[str, int],
    d_text: str,
) -> list[dict]:
    cfc_addr = name_to_addr.get("ibt_x_cf_check")
    if cfc_addr is None:
        return []

    has_endbr = function_starts_with_endbr(d_text, cfc_addr)
    if has_endbr is False:
        return [{
            "category": "CALLEE_INSTRUMENTATION",
            "issue": "CF_CHECK_NO_ENDBR",
            "target_addr": f"0x{cfc_addr:x}",
            "target_symbols": ["ibt_x_cf_check"],
            "func_attr": "cf_check",
            "call_mode": "plain",
            "weird_attr": "",
            "expected": "YES",
            "observed": "MISSING",
            "details": "cf_check function lacks endbr64",
        }]
    return []



def _callee_bug(
    issue: str, addr: int, symbols: list[str], plan_row: dict, details: str,
) -> dict:
    observed = "PRESENT" if issue == "UNEXPECTED_ENDBR" else "MISSING"
    expected = "NO" if issue == "UNEXPECTED_ENDBR" else "YES"
    return {
        "category": "CALLEE_INSTRUMENTATION",
        "issue": issue,
        "target_addr": f"0x{addr:x}",
        "target_symbols": symbols,
        "func_attr": plan_row["func_attr"],
        "call_mode": plan_row["call_mode"],
        "weird_attr": plan_row["weird_attr"],
        "expected": expected,
        "observed": observed,
        "details": details,
    }


def _callsite_bug(
    issue: str, addr: str, shim: str, plan_row: dict,
    mnemonic: str, raw_bytes: str, details: str,
) -> dict:
    expected = "notrack prefix" if issue == "MISSING_NOTRACK" else "no notrack"
    return {
        "category": "CALLSITE_INSTRUMENTATION",
        "issue": issue,
        "target_addr": f"0x{addr}",
        "target_symbols": [shim],
        "func_attr": plan_row["func_attr"],
        "call_mode": plan_row["call_mode"],
        "weird_attr": plan_row["weird_attr"],
        "expected": expected,
        "observed": mnemonic,
        "details": details,
    }


def _unmapped_record(name: str, expect_notrack: bool) -> dict:
    return {
        "target": name,
        "expected_notrack": expect_notrack,
        "mapped": False,
        "observed_notrack": False,
        "callsite_addr": "",
    }
