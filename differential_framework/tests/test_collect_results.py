"""
Tests for runner.collect_results — JSON → CSV aggregation.

Verifies that the collect_results script correctly appends analysis
JSON data to each of the suite's CSV files.
"""

import csv
import json
from pathlib import Path

import pytest


# ── Fixture: minimal analysis JSON ───────────────────────────────────

ANALYSIS = {
    "test_id": "42",
    "config": "gcc-branch-baseline",
    "total_funcs": 10,
    "target_funcs": 3,
    "total_endbr64": 8,
    "addr_taken_endbr_sites": 2,
    "callsites_mapped": 2,
    "callsites_nocf_expected": 1,
    "callsites_nocf_observed": 1,
    "callee_bugs": 1,
    "callsite_bugs": 0,
    "alias_groups": 1,
    "aliases": [
        {"addr": "0x401010", "symbols": ["func_2", "func_2_alias"]},
    ],
    "bugs": [
        {
            "category": "CALLEE_INSTRUMENTATION",
            "issue": "UNEXPECTED_ENDBR",
            "target_addr": "0x401000",
            "target_symbols": ["func_1"],
            "func_attr": "nocf_check",
            "call_mode": "nocf_ptr",
            "weird_attr": "none",
            "expected": "NO",
            "observed": "PRESENT",
            "details": "nocf_check function has endbr64 at entry",
        },
    ],
    "total_bugs": 1,
    "target_status": [
        {"name": "func_1", "status": "PRESENT"},
        {"name": "func_2", "status": "MISSING"},
    ],
    "callsite_records": [
        {
            "target": "func_1",
            "expected_notrack": True,
            "mapped": True,
            "observed_notrack": True,
            "callsite_addr": "0x40110f",
        },
    ],
    "jumptable": {
        "table_detected": True,
        "indirect_jmp_count": 1,
        "indirect_jmp_notrack": False,
    },
}


@pytest.fixture
def csv_env(tmp_path):
    """Create CSV files with headers and return their paths + JSON path."""
    json_path = str(tmp_path / "analysis.json")
    Path(json_path).write_text(json.dumps(ANALYSIS))

    files = {
        "summary": tmp_path / "summary.csv",
        "bugs": tmp_path / "bugs.csv",
        "aliases": tmp_path / "aliases.csv",
        "endbr": tmp_path / "endbr64_counts.csv",
        "jumptable": tmp_path / "jumptable.csv",
        "callsite": tmp_path / "callsite_detail.csv",
    }

    files["summary"].write_text(
        "test_id,config,total_funcs,target_funcs,addr_taken_endbr_sites,"
        "callsites_mapped,callsites_nocf_expected,callsites_nocf_observed,"
        "callee_bugs,callsite_bugs,alias_groups\n"
    )
    files["bugs"].write_text(
        "test_id,config,category,issue,target_addr,target_symbols,"
        "func_attr,call_mode,weird_attr,expected,observed,details\n"
    )
    files["aliases"].write_text("test_id,config,addr,symbols\n")
    files["endbr"].write_text("test_id,config,total_endbr64\n")
    files["jumptable"].write_text(
        "test_id,config,switch_table_detected,indirect_jmp_count,indirect_jmp_notrack\n"
    )
    files["callsite"].write_text(
        "test_id,config,target,expected_notrack,mapped,observed_notrack,callsite_addr\n"
    )

    return json_path, files


class TestCollectResults:
    def _run_collector(self, json_path, files):
        """Import and run the collector inline (avoids subprocess)."""
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location(
            "collect_results",
            str(Path(__file__).resolve().parent.parent / "runner" / "collect_results.py"),
        )
        mod = importlib.util.module_from_spec(spec)

        # Patch sys.argv.
        original_argv = sys.argv
        sys.argv = [
            "collect_results.py",
            json_path,
            str(files["summary"]),
            str(files["bugs"]),
            str(files["aliases"]),
            str(files["endbr"]),
            str(files["jumptable"]),
            str(files["callsite"]),
        ]
        try:
            spec.loader.exec_module(mod)
            mod.main()
        finally:
            sys.argv = original_argv

    def test_summary_row(self, csv_env):
        json_path, files = csv_env
        self._run_collector(json_path, files)

        with open(files["summary"], newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["test_id"] == "42"
        assert rows[0]["config"] == "gcc-branch-baseline"
        assert rows[0]["callee_bugs"] == "1"

    def test_bug_row(self, csv_env):
        json_path, files = csv_env
        self._run_collector(json_path, files)

        with open(files["bugs"], newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["issue"] == "UNEXPECTED_ENDBR"
        assert rows[0]["target_symbols"] == "func_1"

    def test_alias_row(self, csv_env):
        json_path, files = csv_env
        self._run_collector(json_path, files)

        with open(files["aliases"], newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert "func_2" in rows[0]["symbols"]
        assert "func_2_alias" in rows[0]["symbols"]

    def test_endbr_count_row(self, csv_env):
        json_path, files = csv_env
        self._run_collector(json_path, files)

        with open(files["endbr"], newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["total_endbr64"] == "8"

    def test_jumptable_row(self, csv_env):
        json_path, files = csv_env
        self._run_collector(json_path, files)

        with open(files["jumptable"], newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["switch_table_detected"] == "True"

    def test_callsite_row(self, csv_env):
        json_path, files = csv_env
        self._run_collector(json_path, files)

        with open(files["callsite"], newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["target"] == "func_1"
        assert rows[0]["callsite_addr"] == "0x40110f"
