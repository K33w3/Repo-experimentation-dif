"""
Tests for generator.plan — target selection, attribute assignment, and output.

Verifies randomised target selection, attribute distribution, source
rewriting, and CSV/target-list file output.
"""

import csv
import random
import tempfile
from pathlib import Path

import pytest

from generator.plan import (
    assign_attributes,
    build_attrs,
    rewrite_source,
    select_targets,
    write_plan,
    write_targets,
)


# ── Fixtures ─────────────────────────────────────────────────────────

SAMPLE_PROTOS = {
    "func_1": "int32_t func_1(int32_t p1)",
    "func_2": "uint64_t func_2(void)",
    "func_3": "int32_t func_3(int32_t a, uint64_t b)",
    "func_4": "int16_t func_4(int16_t x)",
}


# ── Tests: select_targets ────────────────────────────────────────────

class TestSelectTargets:
    def test_selects_within_bounds(self):
        rng = random.Random(42)
        targets = select_targets(SAMPLE_PROTOS, rng, 2, 4)
        assert 2 <= len(targets) <= 4
        for t in targets:
            assert t in SAMPLE_PROTOS

    def test_respects_max(self):
        rng = random.Random(42)
        targets = select_targets(SAMPLE_PROTOS, rng, 1, 2)
        assert len(targets) <= 2

    def test_deterministic_with_seed(self):
        t1 = select_targets(SAMPLE_PROTOS, random.Random(123), 2, 4)
        t2 = select_targets(SAMPLE_PROTOS, random.Random(123), 2, 4)
        assert t1 == t2

    def test_empty_protos(self):
        targets = select_targets({}, random.Random(42), 2, 4)
        assert targets == []

    def test_complex_only_protos(self):
        """All functions are complex → empty selection."""
        complex_protos = {
            "func_1": "int32_t func_1(struct S s)",
            "func_2": "int32_t func_2(int a, ...)",
        }
        targets = select_targets(complex_protos, random.Random(42), 1, 2)
        assert targets == []


# ── Tests: assign_attributes ────────────────────────────────────────

class TestAssignAttributes:
    def test_assigns_to_all_targets(self):
        rng = random.Random(42)
        targets = ["func_1", "func_2", "func_3"]
        rows = assign_attributes(targets, SAMPLE_PROTOS, rng)
        assert len(rows) == 3
        for row in rows:
            assert row["name"] in targets
            assert row["func_attr"] in ("nocf_check", "cf_check", "none")
            assert row["call_mode"] in ("nocf_ptr", "plain")
            assert row["weird_attr"] in ("none", "hidden", "used")
            assert row["expected_endbr"] in ("YES", "NO", "ANY")

    def test_nocf_check_implies_nocf_ptr(self):
        """When func_attr is nocf_check, call_mode must be nocf_ptr."""
        rng = random.Random(42)
        rows = assign_attributes(list(SAMPLE_PROTOS.keys()), SAMPLE_PROTOS, rng)
        for row in rows:
            if row["func_attr"] == "nocf_check":
                assert row["call_mode"] == "nocf_ptr"
                assert row["expected_endbr"] == "NO"

    def test_deterministic(self):
        r1 = assign_attributes(["func_1", "func_2"], SAMPLE_PROTOS, random.Random(99))
        r2 = assign_attributes(["func_1", "func_2"], SAMPLE_PROTOS, random.Random(99))
        assert r1 == r2


# ── Tests: build_attrs ───────────────────────────────────────────────

class TestBuildAttrs:
    def test_nocf_check(self):
        row = {"func_attr": "nocf_check", "weird_attr": "none"}
        result = build_attrs(row)
        assert "__attribute__((nocf_check))" in result
        assert "__attribute__((noinline))" in result

    def test_cf_check(self):
        row = {"func_attr": "cf_check", "weird_attr": "none"}
        result = build_attrs(row)
        assert "__attribute__((cf_check))" in result

    def test_hidden_visibility(self):
        row = {"func_attr": "none", "weird_attr": "hidden"}
        result = build_attrs(row)
        assert 'visibility("hidden")' in result

    def test_used(self):
        row = {"func_attr": "none", "weird_attr": "used"}
        result = build_attrs(row)
        assert "__attribute__((used))" in result

    def test_plain(self):
        row = {"func_attr": "none", "weird_attr": "none"}
        result = build_attrs(row)
        assert result == "__attribute__((noinline))"


# ── Tests: write_plan / write_targets ────────────────────────────────

class TestFileOutput:
    def test_write_plan_csv(self, tmp_path):
        rows = [
            {
                "name": "func_1", "prototype": "int32_t func_1(void)",
                "func_attr": "nocf_check", "call_mode": "nocf_ptr",
                "weird_attr": "none", "expected_endbr": "NO",
            },
        ]
        plan_path = str(tmp_path / "plan.csv")
        write_plan(rows, plan_path)

        with open(plan_path, newline="") as f:
            reader = csv.DictReader(f)
            data = list(reader)
        assert len(data) == 1
        assert data[0]["function"] == "func_1"
        assert data[0]["expected_endbr"] == "NO"

    def test_write_targets_txt(self, tmp_path):
        rows = [
            {"name": "func_1", "prototype": ""},
            {"name": "func_2", "prototype": ""},
        ]
        targets_path = str(tmp_path / "targets.txt")
        write_targets(rows, targets_path)

        content = Path(targets_path).read_text()
        assert "func_1\n" in content
        assert "func_2\n" in content


# ── Tests: rewrite_source ────────────────────────────────────────────

class TestRewriteSource:
    def test_injects_attributes(self):
        lines = [
            "int32_t func_1(int32_t p1);\n",
            "\n",
            "int32_t func_1(int32_t p1) {\n",
            "    return p1;\n",
            "}\n",
        ]
        row_map = {
            "func_1": {
                "name": "func_1",
                "prototype": "int32_t func_1(int32_t p1)",
                "func_attr": "nocf_check",
                "weird_attr": "none",
            },
        }
        result = rewrite_source(lines, row_map)
        # Both prototype and definition should have nocf_check.
        joined = "".join(result)
        assert "nocf_check" in joined
        assert "__attribute__((noinline))" in joined

    def test_leaves_non_targets_alone(self):
        lines = [
            "int32_t func_1(int32_t p1);\n",
            "int32_t func_2(void);\n",
        ]
        row_map = {
            "func_1": {
                "name": "func_1",
                "prototype": "int32_t func_1(int32_t p1)",
                "func_attr": "nocf_check",
                "weird_attr": "none",
            },
        }
        result = rewrite_source(lines, row_map)
        # func_2 should be unchanged.
        assert result[1] == "int32_t func_2(void);\n"
