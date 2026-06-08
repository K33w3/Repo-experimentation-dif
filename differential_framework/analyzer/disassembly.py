#!/usr/bin/env python3
"""
Disassembly and parsing utils: we operate on the text output of the initial objdump -d to extract the structural information such as: indirect call/jmp sites, full function bodies, instruction bytes
"""

import re

from .symbols import ENDBR_BYTES, NOTRACK_BYTE, run

def disasm(binary: str) -> str:
    return run(["objdump", "-d", binary]).stdout


def first_insn_bytes_at_addr(d_text: str, addr: int) -> str | None:
    hex_addr = f"{addr:x}"
    pat = re.compile(
        rf"^\s*{hex_addr}:\s+((?:[0-9a-f]{{2}}\s+)+)\S",
        re.MULTILINE,
    )
    m = pat.search(d_text)
    if not m:
        return None
    return m.group(1).replace(" ", "").strip()


def function_starts_with_endbr(d_text: str, addr: int) -> bool | None:
    raw = first_insn_bytes_at_addr(d_text, addr)
    if raw is None:
        return None
    return raw.startswith(ENDBR_BYTES)


def count_total_endbr(d_text: str) -> int:    
    return d_text.lower().count("endbr64")

def extract_function_body(d_text: str, sym: str) -> str | None:
    anchor = re.compile(
        rf"^[0-9a-f]+\s+<{re.escape(sym)}>:\s*$",
        re.MULTILINE,
    )
    m = anchor.search(d_text)
    if not m:
        return None

    rest = d_text[m.end():]
    end_m = re.search(r"\n\s*\n", rest)
    if end_m:
        return rest[: end_m.start()]
    return rest


_INSN_LINE = re.compile(
    r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(\S.*)$",
    re.MULTILINE,
)

def find_indirect_calls(body_text: str | None) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    if body_text is None:
        return results

    for m in _INSN_LINE.finditer(body_text):
        addr, bytes_s, mnem = m.group(1), m.group(2), m.group(3)
        mnem = mnem.split("#", 1)[0].strip() 
        if re.match(r"^(?:notrack\s+)?(?:call|jmp)\s+\*", mnem):
            results.append((addr, bytes_s.replace(" ", "").strip(), mnem))

    return results


def callsite_has_notrack(bytes_hex: str, mnemonic: str) -> bool:
    mnem_says = mnemonic.startswith("notrack ")
    bytes_says = bytes_hex.startswith(NOTRACK_BYTE)
    return mnem_says and bytes_says
