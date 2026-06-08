"""
Tests for analyzer.disassembly — objdump output parsing.

Uses realistic objdump snippets to verify instruction-byte extraction,
ENDBR64 detection, function-body parsing, and indirect-call identification.
"""

import pytest

from analyzer.disassembly import (
    callsite_has_notrack,
    count_total_endbr,
    extract_function_body,
    find_indirect_calls,
    first_insn_bytes_at_addr,
    function_starts_with_endbr,
)


# ── Realistic objdump fragments ─────────────────────────────────────

# Function starting with endbr64.
DISASM_WITH_ENDBR = """\
0000000000401000 <func_1>:
  401000:	f3 0f 1e fa          	endbr64
  401004:	55                   	push   %rbp
  401005:	48 89 e5             	mov    %rsp,%rbp
  401008:	89 7d fc             	mov    %edi,-0x4(%rbp)
  40100b:	8b 45 fc             	mov    -0x4(%rbp),%eax
  40100e:	5d                   	pop    %rbp
  40100f:	c3                   	ret

0000000000401010 <func_2>:
  401010:	55                   	push   %rbp
  401011:	48 89 e5             	mov    %rsp,%rbp
"""

# Shim with a notrack indirect call.
DISASM_NOTRACK_SHIM = """\
0000000000401100 <ibt_callsite_func_1>:
  401100:	f3 0f 1e fa          	endbr64
  401104:	55                   	push   %rbp
  401105:	48 89 e5             	mov    %rsp,%rbp
  401108:	48 8b 05 f1 2e 00 00 	mov    0x2ef1(%rip),%rax
  40110f:	3e ff d0             	notrack call *%rax
  401112:	5d                   	pop    %rbp
  401113:	c3                   	ret

"""

# Shim with a plain indirect call (no notrack).
DISASM_PLAIN_SHIM = """\
0000000000401200 <ibt_callsite_func_2>:
  401200:	f3 0f 1e fa          	endbr64
  401204:	55                   	push   %rbp
  401205:	48 89 e5             	mov    %rsp,%rbp
  401208:	48 8b 05 f1 2e 00 00 	mov    0x2ef1(%rip),%rax
  40120f:	ff d0                	call   *%rax
  401211:	5d                   	pop    %rbp
  401212:	c3                   	ret

"""

# Shim with an indirect jmp (tail call optimisation).
DISASM_TAILCALL_SHIM = """\
0000000000401300 <ibt_callsite_func_3>:
  401300:	f3 0f 1e fa          	endbr64
  401304:	48 8b 05 f1 2e 00 00 	mov    0x2ef1(%rip),%rax
  40130b:	3e ff e0             	notrack jmp *%rax

"""

# Shim with no indirect call (compiler devirtualised).
DISASM_DEVIRT_SHIM = """\
0000000000401400 <ibt_callsite_func_4>:
  401400:	f3 0f 1e fa          	endbr64
  401404:	e8 f7 fb ff ff       	call   401000 <func_1>
  401409:	c3                   	ret

"""


# ── Tests: first_insn_bytes_at_addr ──────────────────────────────────

class TestFirstInsnBytes:
    def test_endbr64_bytes(self):
        result = first_insn_bytes_at_addr(DISASM_WITH_ENDBR, 0x401000)
        assert result == "f30f1efa"

    def test_push_rbp_bytes(self):
        result = first_insn_bytes_at_addr(DISASM_WITH_ENDBR, 0x401010)
        assert result == "55"

    def test_nonexistent_address(self):
        result = first_insn_bytes_at_addr(DISASM_WITH_ENDBR, 0xDEAD)
        assert result is None


# ── Tests: function_starts_with_endbr ────────────────────────────────

class TestFunctionStartsWithEndbr:
    def test_has_endbr(self):
        assert function_starts_with_endbr(DISASM_WITH_ENDBR, 0x401000) is True

    def test_no_endbr(self):
        assert function_starts_with_endbr(DISASM_WITH_ENDBR, 0x401010) is False

    def test_missing_address(self):
        assert function_starts_with_endbr(DISASM_WITH_ENDBR, 0xDEAD) is None


# ── Tests: count_total_endbr ─────────────────────────────────────────

class TestCountTotalEndbr:
    def test_counts_all(self):
        full = DISASM_WITH_ENDBR + DISASM_NOTRACK_SHIM + DISASM_PLAIN_SHIM
        # func_1, ibt_callsite_func_1, ibt_callsite_func_2 = 3
        assert count_total_endbr(full) == 3

    def test_empty(self):
        assert count_total_endbr("") == 0


# ── Tests: extract_function_body ─────────────────────────────────────

class TestExtractFunctionBody:
    def test_extracts_shim(self):
        body = extract_function_body(DISASM_NOTRACK_SHIM, "ibt_callsite_func_1")
        assert body is not None
        assert "notrack call" in body
        assert "push" in body

    def test_missing_function(self):
        body = extract_function_body(DISASM_NOTRACK_SHIM, "nonexistent")
        assert body is None

    def test_body_stops_at_blank_line(self):
        combined = DISASM_WITH_ENDBR  # has blank line between func_1 and func_2
        body = extract_function_body(combined, "func_1")
        assert body is not None
        assert "func_2" not in body


# ── Tests: find_indirect_calls ───────────────────────────────────────

class TestFindIndirectCalls:
    def test_notrack_call(self):
        body = extract_function_body(DISASM_NOTRACK_SHIM, "ibt_callsite_func_1")
        calls = find_indirect_calls(body)
        assert len(calls) == 1
        addr, raw_bytes, mnem = calls[0]
        assert "notrack" in mnem
        assert raw_bytes.startswith("3e")

    def test_plain_call(self):
        body = extract_function_body(DISASM_PLAIN_SHIM, "ibt_callsite_func_2")
        calls = find_indirect_calls(body)
        assert len(calls) == 1
        _, raw_bytes, mnem = calls[0]
        assert "notrack" not in mnem
        assert not raw_bytes.startswith("3e")

    def test_tail_call_jmp(self):
        body = extract_function_body(DISASM_TAILCALL_SHIM, "ibt_callsite_func_3")
        calls = find_indirect_calls(body)
        assert len(calls) == 1
        _, _, mnem = calls[0]
        assert "jmp" in mnem

    def test_devirtualised_no_indirect(self):
        body = extract_function_body(DISASM_DEVIRT_SHIM, "ibt_callsite_func_4")
        calls = find_indirect_calls(body)
        assert len(calls) == 0

    def test_none_body(self):
        assert find_indirect_calls(None) == []


# ── Tests: callsite_has_notrack ──────────────────────────────────────

class TestCallsiteHasNotrack:
    def test_has_notrack(self):
        assert callsite_has_notrack("3effd0", "notrack call *%rax") is True

    def test_plain_call(self):
        assert callsite_has_notrack("ffd0", "call *%rax") is False

    def test_bytes_mismatch_mnem(self):
        # Bytes say notrack but mnemonic doesn't — should be False (disagreement).
        assert callsite_has_notrack("3effd0", "call *%rax") is False

    def test_mnem_mismatch_bytes(self):
        # Mnemonic says notrack but bytes don't — should be False.
        assert callsite_has_notrack("ffd0", "notrack call *%rax") is False
