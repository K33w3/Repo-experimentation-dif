"""
Tests for analyzer.oracles — verification oracle logic.

Constructs synthetic disassembly and plan data to test each oracle's
bug detection and observation logic in isolation.
"""

import pytest

from analyzer.oracles import (
    check_callee_endbr,
    check_callsite_notrack,
    check_cf_check,
    observe_jumptable,
)


# ── Synthetic disassembly for oracle tests ───────────────────────────

# Two functions: func_1 has endbr64, func_2 does not.
DISASM_ORACLE = """\
0000000000401000 <func_1>:
  401000:	f3 0f 1e fa          	endbr64
  401004:	55                   	push   %rbp
  401005:	c3                   	ret

0000000000401010 <func_2>:
  401010:	55                   	push   %rbp
  401011:	c3                   	ret

0000000000401100 <ibt_callsite_func_1>:
  401100:	f3 0f 1e fa          	endbr64
  401104:	48 8b 05 f1 2e 00 00 	mov    0x2ef1(%rip),%rax
  40110b:	3e ff d0             	notrack call *%rax
  40110e:	c3                   	ret

0000000000401200 <ibt_callsite_func_2>:
  401200:	f3 0f 1e fa          	endbr64
  401204:	48 8b 05 f1 2e 00 00 	mov    0x2ef1(%rip),%rax
  40120b:	ff d0                	call   *%rax
  40120d:	c3                   	ret

0000000000401300 <ibt_x_cf_check>:
  401300:	f3 0f 1e fa          	endbr64
  401304:	48 31 c0             	xor    %rax,%rax
  401307:	c3                   	ret

"""

# cf_check function WITHOUT endbr64 (bug case).
DISASM_CF_CHECK_BUG = """\
0000000000401300 <ibt_x_cf_check>:
  401300:	55                   	push   %rbp
  401301:	c3                   	ret

"""

# Jump-table with indirect jmp.
DISASM_JUMPTABLE = """\
0000000000401400 <ibt_x_jumptable>:
  401400:	f3 0f 1e fa          	endbr64
  401404:	8b 05 00 00 00 00    	mov    0x0(%rip),%eax
  40140a:	ff 24 c5 00 00 00 00 	jmp    *0x0(,%rax,8)
  401411:	c3                   	ret

"""

# ── Fixtures ─────────────────────────────────────────────────────────

ADDR_MAP = {
    0x401000: [("func_1", "T", 16)],
    0x401010: [("func_2", "T", 16)],
}

NAME_TO_ADDR = {"func_1": 0x401000, "func_2": 0x401010}

PLAN_NOCF_CHECK = {
    "func_1": {
        "function": "func_1", "expected_endbr": "NO",
        "func_attr": "nocf_check", "call_mode": "nocf_ptr", "weird_attr": "none",
    },
}

PLAN_EXPECT_ENDBR = {
    "func_2": {
        "function": "func_2", "expected_endbr": "YES",
        "func_attr": "none", "call_mode": "plain", "weird_attr": "none",
    },
}

PLAN_BOTH = {**PLAN_NOCF_CHECK, **PLAN_EXPECT_ENDBR}


# ── Tests: check_callee_endbr ────────────────────────────────────────

class TestCheckCalleeEndbr:
    def test_unexpected_endbr_bug(self):
        """nocf_check function HAS endbr64 → UNEXPECTED_ENDBR bug."""
        bugs, status, sites, count = check_callee_endbr(
            ["func_1"], PLAN_NOCF_CHECK, NAME_TO_ADDR, ADDR_MAP, DISASM_ORACLE,
        )
        assert count == 1
        assert bugs[0]["issue"] == "UNEXPECTED_ENDBR"
        assert bugs[0]["category"] == "CALLEE_INSTRUMENTATION"

    def test_missing_endbr_bug(self):
        """Normal function LACKS endbr64 → MISSING_ENDBR bug."""
        bugs, status, sites, count = check_callee_endbr(
            ["func_2"], PLAN_EXPECT_ENDBR, NAME_TO_ADDR, ADDR_MAP, DISASM_ORACLE,
        )
        assert count == 1
        assert bugs[0]["issue"] == "MISSING_ENDBR"

    def test_no_bug_when_correct(self):
        """Function with expected_endbr=YES that has endbr64 → no bug."""
        plan = {
            "func_1": {
                "function": "func_1", "expected_endbr": "YES",
                "func_attr": "none", "call_mode": "plain", "weird_attr": "none",
            },
        }
        bugs, status, sites, count = check_callee_endbr(
            ["func_1"], plan, NAME_TO_ADDR, ADDR_MAP, DISASM_ORACLE,
        )
        assert count == 0
        assert len(bugs) == 0
        assert sites == 1  # func_1 does have endbr64

    def test_absent_target(self):
        """Target not found in binary → ABSENT status, no bug."""
        plan_with_99 = {
            "func_99": {
                "function": "func_99", "expected_endbr": "YES",
                "func_attr": "none", "call_mode": "plain", "weird_attr": "none",
            },
        }
        bugs, status, _, _ = check_callee_endbr(
            ["func_99"], plan_with_99, NAME_TO_ADDR, ADDR_MAP, DISASM_ORACLE,
        )
        assert len(bugs) == 0
        assert status[0]["status"] == "ABSENT"

    def test_missing_plan(self):
        """Target not in plan → NOPLAN status, no bug."""
        bugs, status, _, _ = check_callee_endbr(
            ["func_1"], {}, NAME_TO_ADDR, ADDR_MAP, DISASM_ORACLE,
        )
        assert len(bugs) == 0
        assert status[0]["status"] == "NOPLAN"

    def test_alias_dedup(self):
        """Aliased addresses are checked only once."""
        alias_addr_map = {
            0x401000: [("func_1", "T", 16), ("func_1_alias", "T", 16)],
        }
        alias_name_to_addr = {"func_1": 0x401000, "func_1_alias": 0x401000}
        plan = {
            "func_1": {**PLAN_NOCF_CHECK["func_1"]},
            "func_1_alias": {**PLAN_NOCF_CHECK["func_1"], "function": "func_1_alias"},
        }
        bugs, _, _, count = check_callee_endbr(
            ["func_1", "func_1_alias"], plan, alias_name_to_addr,
            alias_addr_map, DISASM_ORACLE,
        )
        # Only one bug even though two names map to the same address.
        assert count == 1


# ── Tests: check_callsite_notrack ────────────────────────────────────

class TestCheckCallsiteNotrack:
    def test_missing_notrack_bug(self):
        """nocf_ptr call WITHOUT notrack → MISSING_NOTRACK."""
        plan = {
            "func_2": {
                "function": "func_2", "call_mode": "nocf_ptr",
                "func_attr": "nocf_check", "weird_attr": "none",
            },
        }
        bugs, records, mapped, exp, obs, count = check_callsite_notrack(
            ["func_2"], plan, DISASM_ORACLE,
        )
        assert count == 1
        assert bugs[0]["issue"] == "MISSING_NOTRACK"

    def test_correct_notrack(self):
        """nocf_ptr call WITH notrack → no bug."""
        plan = {
            "func_1": {
                "function": "func_1", "call_mode": "nocf_ptr",
                "func_attr": "nocf_check", "weird_attr": "none",
            },
        }
        bugs, records, mapped, exp, obs, count = check_callsite_notrack(
            ["func_1"], plan, DISASM_ORACLE,
        )
        assert count == 0
        assert mapped == 1
        assert obs == 1  # notrack observed

    def test_unexpected_notrack_bug(self):
        """plain call WITH notrack → UNEXPECTED_NOTRACK."""
        plan = {
            "func_1": {
                "function": "func_1", "call_mode": "plain",
                "func_attr": "none", "weird_attr": "none",
            },
        }
        bugs, _, _, _, _, count = check_callsite_notrack(
            ["func_1"], plan, DISASM_ORACLE,
        )
        assert count == 1
        assert bugs[0]["issue"] == "UNEXPECTED_NOTRACK"

    def test_unmapped_shim(self):
        """Missing shim → mapped=False, no bug."""
        plan = {
            "func_99": {
                "function": "func_99", "call_mode": "nocf_ptr",
                "func_attr": "nocf_check", "weird_attr": "none",
            },
        }
        bugs, records, mapped, _, _, count = check_callsite_notrack(
            ["func_99"], plan, DISASM_ORACLE,
        )
        assert count == 0
        assert mapped == 0
        assert records[0]["mapped"] is False


# ── Tests: check_cf_check ────────────────────────────────────────────

class TestCheckCfCheck:
    def test_cf_check_has_endbr(self):
        """cf_check function with endbr64 → no bug."""
        name_to_addr = {"ibt_x_cf_check": 0x401300}
        bugs = check_cf_check(name_to_addr, DISASM_ORACLE)
        assert len(bugs) == 0

    def test_cf_check_missing_endbr(self):
        """cf_check function without endbr64 → CF_CHECK_NO_ENDBR."""
        name_to_addr = {"ibt_x_cf_check": 0x401300}
        bugs = check_cf_check(name_to_addr, DISASM_CF_CHECK_BUG)
        assert len(bugs) == 1
        assert bugs[0]["issue"] == "CF_CHECK_NO_ENDBR"

    def test_cf_check_absent(self):
        """cf_check function not in binary → no bug (no crash)."""
        bugs = check_cf_check({}, DISASM_ORACLE)
        assert len(bugs) == 0


# ── Tests: observe_jumptable ─────────────────────────────────────────

class TestObserveJumptable:
    def test_detects_indirect_jmp(self):
        result = observe_jumptable(DISASM_JUMPTABLE)
        assert result["table_detected"] is True
        assert result["indirect_jmp_count"] == 1

    def test_no_jumptable(self):
        result = observe_jumptable(DISASM_ORACLE)
        assert result["table_detected"] is False
        assert result["indirect_jmp_count"] == 0
