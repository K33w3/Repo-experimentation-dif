#!/usr/bin/env python3
"""
Creation of the Harness: creates a per target shim function, each containing exactly one indrect call 
"""

from .signatures import default_arg_for, params_of, split_params

def emit_harness(rows: list[dict], harness_path: str) -> None:
    h: list[str] = []

    _emit_preamble(h, rows)
    _emit_opaque_barriers(h, rows)
    _emit_shims(h, rows)
    _emit_master_driver(h, rows)

    with open(harness_path, "w") as f:
        f.write("".join(h))

def _emit_preamble(h: list[str], rows: list[dict]) -> None:
    
    h.append("#include <stdint.h>\n#include <stddef.h>\n\n")

    for row in rows:
        h.append(f'extern {row["prototype"]};\n')
    h.append("\n")

    h.append("volatile uintptr_t ibt_sink = 0;\n")
    h.append("volatile uint64_t  ibt_seed = 0xA5A5A5A5A5A5A5A5ULL;\n")
    for i in range(len(rows)):
        h.append(f"volatile uint64_t ibt_marker_{i} = 0;\n")
    h.append("\n")


def _emit_opaque_barriers(h: list[str], rows: list[dict]) -> None:
    for row in rows:
        name = row["name"]
        h.append(f"__attribute__((noinline, used))\n")
        h.append(f"static uintptr_t opaque_barrier_{name}(uintptr_t x) {{\n")
        h.append(f"    uintptr_t s = ibt_seed;\n")
        h.append(f'    asm volatile("xor %1, %0\\n\\t" "xor %1, %0\\n\\t"\n')
        h.append(f'                 : "+r"(x) : "r"(s) : "memory");\n')
        h.append(f"    return x;\n")
        h.append(f"}}\n")
    h.append("\n")


def _emit_shims(h: list[str], rows: list[dict]) -> None:
    for i, row in enumerate(rows):
        name = row["name"]
        sig = row["prototype"]
        params = split_params(params_of(sig))
        args = ", ".join(default_arg_for(p) for p in params)
        tname = f"{name}_fp_t"

        if row["call_mode"] == "nocf_ptr":
            sig_for_td = sig.replace(
                name, f"(* __attribute__((nocf_check)) {tname})", 1,
            )
        else:
            sig_for_td = sig.replace(name, f"(*{tname})", 1)

        h.append(f"__attribute__((noinline, used))\n")
        h.append(f"void ibt_callsite_{name}(void) {{\n")
        h.append(f"    typedef {sig_for_td};\n")
        
        if row["call_mode"] == "nocf_ptr":
            h.append(f"    __attribute__((nocf_check)) {tname} p = (__attribute__((nocf_check)) {tname})opaque_barrier_{name}((uintptr_t)&{name});\n")
            call_expr = f"(*p)({args})" if args else "(*p)()"
        else:
            h.append(f"    {tname} p = ({tname})opaque_barrier_{name}((uintptr_t)&{name});\n")
            call_expr = f"p({args})" if args else "p()"
            
        h.append(f"    ibt_marker_{i} = (uint64_t)(uintptr_t)p + {i};\n")
        h.append(f'    asm volatile("" ::: "memory");\n')
        h.append(f"    (void){call_expr};\n")
        h.append(f'    asm volatile("" ::: "memory");\n')
        h.append(f"}}\n\n")


def _emit_master_driver(h: list[str], rows: list[dict]) -> None:
    h.append("__attribute__((noinline, used)) void ibt_test_harness(void) {\n")
    for row in rows:
        h.append(f'    ibt_callsite_{row["name"]}();\n')
    h.append("    ibt_sink ^= 1;\n")
    h.append("}\n")

    h.append("__attribute__((constructor, used))\n")
    h.append("static void ibt_ctor(void) { ibt_test_harness(); }\n")
