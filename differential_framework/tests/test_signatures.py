"""
Tests for generator.signatures — C function-signature parsing.

Uses CSmith-style source fragments to verify extraction, normalisation,
parameter handling, and simplicity classification.
"""

import pytest

from generator.signatures import (
    collect_prototypes,
    default_arg_for,
    extract_signature,
    is_simple,
    is_top_level,
    normalize_sig,
    params_of,
    split_params,
)


# ── Tests: is_top_level ──────────────────────────────────────────────

class TestIsTopLevel:
    def test_top_level(self):
        assert is_top_level("int func_1(void)") is True

    def test_indented(self):
        assert is_top_level("    int x = 0;") is False

    def test_empty(self):
        assert is_top_level("") is False


# ── Tests: extract_signature ─────────────────────────────────────────

class TestExtractSignature:
    def test_prototype(self):
        result = extract_signature("int32_t func_1(int32_t p1, uint64_t p2);\n")
        assert result is not None
        name, sig, kind, _ = result
        assert name == "func_1"
        assert kind == "prototype"
        assert "p1" in sig

    def test_definition(self):
        result = extract_signature("int32_t func_1(int32_t p1) {\n")
        assert result is not None
        name, _, kind, _ = result
        assert name == "func_1"
        assert kind == "definition"

    def test_definition_no_brace(self):
        """Definition where opening brace is on next line."""
        result = extract_signature("int32_t func_1(int32_t p1)\n")
        assert result is not None
        assert result[2] == "definition"

    def test_rejects_indented(self):
        result = extract_signature("    int32_t func_1(int32_t p1);\n")
        assert result is None

    def test_rejects_return_statement(self):
        result = extract_signature("return func_1(x);\n")
        assert result is None

    def test_rejects_if_statement(self):
        result = extract_signature("if (func_1(x)) {\n")
        assert result is None

    def test_rejects_assignment(self):
        result = extract_signature("x = func_1(y);\n")
        assert result is None

    def test_rejects_no_prefix(self):
        """func_1(...) with no return type is rejected."""
        result = extract_signature("func_1(int32_t p1);\n")
        assert result is None

    def test_non_func_name(self):
        """Lines without func_N pattern are ignored."""
        result = extract_signature("int32_t helper(int x);\n")
        assert result is None


# ── Tests: normalize_sig ─────────────────────────────────────────────

class TestNormalizeSig:
    def test_strips_static(self):
        assert normalize_sig("static int32_t func_1(void)") == "int32_t func_1(void)"

    def test_strips_inline(self):
        assert normalize_sig("inline int32_t func_1(void)") == "int32_t func_1(void)"

    def test_strips_attribute(self):
        result = normalize_sig("__attribute__((noinline)) int32_t func_1(void)")
        assert result == "int32_t func_1(void)"

    def test_strips_multiple(self):
        result = normalize_sig("static inline __attribute__((used)) int32_t func_1(void)")
        assert result == "int32_t func_1(void)"

    def test_preserves_plain(self):
        assert normalize_sig("int32_t func_1(void)") == "int32_t func_1(void)"


# ── Tests: params_of / split_params ──────────────────────────────────

class TestParamHandling:
    def test_params_of(self):
        assert params_of("int32_t func_1(int32_t a, uint64_t b)") == "int32_t a, uint64_t b"

    def test_params_of_void(self):
        assert params_of("int32_t func_1(void)") == "void"

    def test_split_simple(self):
        result = split_params("int32_t a, uint64_t b, int16_t c")
        assert result == ["int32_t a", "uint64_t b", "int16_t c"]

    def test_split_void(self):
        assert split_params("void") == []

    def test_split_empty(self):
        assert split_params("") == []

    def test_split_nested(self):
        """Commas inside nested parens are not split points."""
        result = split_params("void (*fp)(int, int), int x")
        assert len(result) == 2
        assert "(*fp)(int, int)" in result[0]


# ── Tests: is_simple ─────────────────────────────────────────────────

class TestIsSimple:
    def test_simple_scalars(self):
        assert is_simple("int32_t func_1(int32_t a, uint64_t b)") is True

    def test_void_params(self):
        assert is_simple("int32_t func_1(void)") is True

    def test_no_params(self):
        assert is_simple("int32_t func_1()") is True

    def test_variadic(self):
        assert is_simple("int32_t func_1(int32_t a, ...)") is False

    def test_array_param(self):
        assert is_simple("int32_t func_1(int32_t a[10])") is False

    def test_function_pointer(self):
        assert is_simple("int32_t func_1(void (*fp)(int))") is False

    def test_struct_by_value(self):
        assert is_simple("int32_t func_1(struct S s)") is False

    def test_struct_pointer(self):
        """Struct pointers ARE simple (just a pointer)."""
        assert is_simple("int32_t func_1(struct S *s)") is True


# ── Tests: default_arg_for ───────────────────────────────────────────

class TestDefaultArgFor:
    def test_always_zero(self):
        assert default_arg_for("int32_t x") == "0"
        assert default_arg_for("uint64_t *p") == "0"


# ── Tests: collect_prototypes ────────────────────────────────────────

class TestCollectPrototypes:
    def test_collects_from_prototypes(self):
        lines = [
            "int32_t func_1(int32_t p1);\n",
            "uint64_t func_2(void);\n",
            "\n",
            "int32_t func_1(int32_t p1) {\n",
            "    return p1;\n",
            "}\n",
        ]
        protos = collect_prototypes(lines)
        assert "func_1" in protos
        assert "func_2" in protos
        # Prototype takes precedence, so should be normalised.
        assert "static" not in protos["func_1"]

    def test_definition_fallback(self):
        """Functions without prototypes are collected from definitions."""
        lines = [
            "int32_t func_3(uint8_t x) {\n",
            "    return x + 1;\n",
            "}\n",
        ]
        protos = collect_prototypes(lines)
        assert "func_3" in protos

    def test_empty_source(self):
        assert collect_prototypes([]) == {}
