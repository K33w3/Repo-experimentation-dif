"""
Tests for generator.harness — harness C-source emission.

Verifies that the generated harness contains the expected structural
elements: extern declarations, opaque barriers, per-target shims with
indirect calls, and the master driver.
"""

import tempfile
from pathlib import Path

import pytest

from generator.harness import emit_harness


# ── Fixtures ─────────────────────────────────────────────────────────

ROWS = [
    {
        "name": "func_1",
        "prototype": "int32_t func_1(int32_t p1)",
        "func_attr": "nocf_check",
        "call_mode": "nocf_ptr",
        "weird_attr": "none",
    },
    {
        "name": "func_2",
        "prototype": "uint64_t func_2(void)",
        "func_attr": "none",
        "call_mode": "plain",
        "weird_attr": "none",
    },
]


@pytest.fixture
def harness_text(tmp_path):
    """Generate a harness and return its content."""
    path = str(tmp_path / "harness.c")
    emit_harness(ROWS, path)
    return Path(path).read_text()


# ── Tests ────────────────────────────────────────────────────────────

class TestEmitHarness:
    def test_includes(self, harness_text):
        assert "#include <stdint.h>" in harness_text
        assert "#include <stddef.h>" in harness_text

    def test_extern_declarations(self, harness_text):
        assert "extern int32_t func_1(int32_t p1);" in harness_text
        assert "extern uint64_t func_2(void);" in harness_text

    def test_volatile_globals(self, harness_text):
        assert "volatile uintptr_t ibt_sink" in harness_text
        assert "volatile uint64_t  ibt_seed" in harness_text
        assert "ibt_marker_0" in harness_text
        assert "ibt_marker_1" in harness_text

    def test_opaque_barriers(self, harness_text):
        assert "opaque_barrier_func_1" in harness_text
        assert "opaque_barrier_func_2" in harness_text
        assert 'asm volatile' in harness_text

    def test_shim_functions(self, harness_text):
        assert "ibt_callsite_func_1" in harness_text
        assert "ibt_callsite_func_2" in harness_text

    def test_nocf_ptr_typedef(self, harness_text):
        """nocf_ptr call mode should produce nocf_check on the typedef."""
        # func_1 uses nocf_ptr.
        assert "__attribute__((nocf_check))" in harness_text

    def test_plain_typedef(self, harness_text):
        """plain call mode should produce a simple typedef."""
        assert "(*func_2_fp_t)" in harness_text

    def test_shim_calls_with_args(self, harness_text):
        """func_1 has one param → shim should call p(0)."""
        assert "(void)p(0);" in harness_text

    def test_shim_calls_void(self, harness_text):
        """func_2 has void params → shim should call p()."""
        assert "(void)p();" in harness_text

    def test_master_driver(self, harness_text):
        assert "ibt_test_harness" in harness_text
        assert "ibt_callsite_func_1();" in harness_text
        assert "ibt_callsite_func_2();" in harness_text

    def test_constructor(self, harness_text):
        assert "__attribute__((constructor" in harness_text
        assert "ibt_ctor" in harness_text
