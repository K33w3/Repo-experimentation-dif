"""
Tests for generator.extras — observational lane generation.

Verifies that the generated extras C file contains the expected
structural elements: jump-table lane, cf_check function, and
address-forcing constructor.
"""

from pathlib import Path

import pytest

from generator.extras import generate_extras


@pytest.fixture
def extras_text(tmp_path):
    """Generate an extras file and return its content."""
    path = str(tmp_path / "extras.c")
    generate_extras(path, seed=42)
    return Path(path).read_text()


class TestGenerateExtras:
    def test_includes(self, extras_text):
        assert "#include <stdint.h>" in extras_text

    def test_volatile_globals(self, extras_text):
        assert "ibt_jt_input" in extras_text
        assert "ibt_jt_sink" in extras_text
        assert "ibt_x_sink" in extras_text

    def test_cf_check_function(self, extras_text):
        assert "ibt_x_cf_check" in extras_text
        assert "__attribute__((noinline, used, cf_check))" in extras_text
        assert "0xDEADBEEFULL" in extras_text

    def test_jumptable_function(self, extras_text):
        assert "ibt_x_jumptable" in extras_text
        assert "switch (k)" in extras_text
        assert "case 0:" in extras_text
        assert "default:" in extras_text

    def test_jumptable_case_count(self, extras_text):
        """Should have between 8 and 16 cases (from rng.randint(8, 16))."""
        case_count = extras_text.count("case ")
        assert 8 <= case_count <= 16

    def test_constructor(self, extras_text):
        assert "__attribute__((constructor, used))" in extras_text
        assert "ibt_x_take_addr" in extras_text
        assert "&ibt_x_cf_check" in extras_text
        assert "&ibt_x_jumptable" in extras_text

    def test_deterministic(self, tmp_path):
        """Same seed produces identical output."""
        p1 = str(tmp_path / "extras1.c")
        p2 = str(tmp_path / "extras2.c")
        generate_extras(p1, seed=99)
        generate_extras(p2, seed=99)
        assert Path(p1).read_text() == Path(p2).read_text()

    def test_different_seeds(self, tmp_path):
        """Different seeds produce different output."""
        p1 = str(tmp_path / "extras_a.c")
        p2 = str(tmp_path / "extras_b.c")
        generate_extras(p1, seed=1)
        generate_extras(p2, seed=2)
        assert Path(p1).read_text() != Path(p2).read_text()
