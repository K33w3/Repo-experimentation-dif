#!/usr/bin/env python3
"""
ELF symbol table Collection: we verify the symbols and grouping by address to record alias groups. This is just for ICF folding purposes.
"""

import subprocess

ENDBR_BYTES = "f30f1efa"
NOTRACK_BYTE = "3e"

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def collect_symbols(binary: str) -> dict[int, list[tuple[str, str, int]]]:
    out = run(["nm", "-S", "--defined-only", "--numeric-sort", binary]).stdout
    addr_map: dict[int, list[tuple[str, str, int]]] = {}

    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 4:
            addr_s, size_s, typ, name = parts
        elif len(parts) == 3:
            addr_s, typ, name = parts
            size_s = "0"
        else:
            continue

        if typ.lower() != "t":
            continue
        try:
            addr = int(addr_s, 16)
            size = int(size_s, 16) if size_s else 0
        except ValueError:
            continue

        addr_map.setdefault(addr, []).append((name, typ, size))

    return addr_map

def build_name_index(
    addr_map: dict[int, list[tuple[str, str, int]]],
) -> dict[str, int]:
    name_to_addr: dict[str, int] = {}
    for addr, syms in addr_map.items():
        for name, _typ, _size in syms:
            name_to_addr[name] = addr
    return name_to_addr


def find_alias_groups(
    addr_map: dict[int, list[tuple[str, str, int]]],
) -> list[dict]:
    return [
        {"addr": f"0x{addr:x}", "symbols": [s[0] for s in syms]}
        for addr, syms in addr_map.items()
        if len(syms) > 1
    ]
