"""
Tests for analyzer.symbols — ELF symbol table collection.

Uses mocked ``nm`` output to verify address grouping, name indexing,
and alias detection without requiring a real binary.
"""

import pytest
from unittest.mock import patch, MagicMock

from analyzer.symbols import (
    build_name_index,
    collect_symbols,
    find_alias_groups,
)


# ── Realistic nm -S output ───────────────────────────────────────────

NM_OUTPUT = """\
0000000000401000 0000000000000010 T func_1
0000000000401010 0000000000000020 T func_2
0000000000401010 0000000000000020 T func_2_alias
0000000000401030 0000000000000008 t helper_local
0000000000402000 0000000000000100 D global_data
0000000000401050 T func_3
"""


def _mock_nm(binary):
    """Return a mock CompletedProcess for nm."""
    result = MagicMock()
    result.stdout = NM_OUTPUT
    return result


class TestCollectSymbols:
    @patch("analyzer.symbols.run", side_effect=_mock_nm)
    def test_collects_text_symbols_only(self, mock_run):
        addr_map = collect_symbols("/fake/binary")
        # Should include T and t symbols, not D.
        all_names = [
            name for syms in addr_map.values() for name, _, _ in syms
        ]
        assert "func_1" in all_names
        assert "func_2" in all_names
        assert "helper_local" in all_names
        assert "global_data" not in all_names

    @patch("analyzer.symbols.run", side_effect=_mock_nm)
    def test_groups_aliases(self, mock_run):
        addr_map = collect_symbols("/fake/binary")
        addr_0x401010 = addr_map[0x401010]
        names = [n for n, _, _ in addr_0x401010]
        assert "func_2" in names
        assert "func_2_alias" in names
        assert len(addr_0x401010) == 2

    @patch("analyzer.symbols.run", side_effect=_mock_nm)
    def test_parses_size(self, mock_run):
        addr_map = collect_symbols("/fake/binary")
        func_1_entry = addr_map[0x401000][0]
        name, typ, size = func_1_entry
        assert name == "func_1"
        assert typ == "T"
        assert size == 0x10

    @patch("analyzer.symbols.run", side_effect=_mock_nm)
    def test_handles_missing_size(self, mock_run):
        addr_map = collect_symbols("/fake/binary")
        # func_3 has no size field in nm output (3-column line).
        func_3_entry = addr_map[0x401050][0]
        assert func_3_entry[0] == "func_3"
        assert func_3_entry[2] == 0  # default size


class TestBuildNameIndex:
    def test_maps_all_names(self):
        addr_map = {
            0x401000: [("func_1", "T", 16)],
            0x401010: [("func_2", "T", 32), ("func_2_alias", "T", 32)],
        }
        idx = build_name_index(addr_map)
        assert idx["func_1"] == 0x401000
        assert idx["func_2"] == 0x401010
        assert idx["func_2_alias"] == 0x401010


class TestFindAliasGroups:
    def test_finds_aliases(self):
        addr_map = {
            0x401000: [("func_1", "T", 16)],
            0x401010: [("func_2", "T", 32), ("func_2_alias", "T", 32)],
        }
        groups = find_alias_groups(addr_map)
        assert len(groups) == 1
        assert set(groups[0]["symbols"]) == {"func_2", "func_2_alias"}

    def test_no_aliases(self):
        addr_map = {
            0x401000: [("func_1", "T", 16)],
            0x401010: [("func_2", "T", 32)],
        }
        groups = find_alias_groups(addr_map)
        assert len(groups) == 0
