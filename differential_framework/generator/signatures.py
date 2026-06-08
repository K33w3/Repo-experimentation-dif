#!/usr/bin/env python3
"""
we extract the function signature and normalise/remove the attributes to normalise the stuff.
"""

import re

_NAME_PAT = re.compile(r"\b(func_\d+)\s*\(")

def is_top_level(line: str) -> bool:
    return bool(line) and not line[0].isspace()


def extract_signature(line: str) -> tuple[str, str, str, int] | None:
    if not is_top_level(line):
        return None

    raw = line.rstrip("\n")
    m = _NAME_PAT.search(raw)
    if not m:
        return None

    prefix = raw[: m.start()].strip()
    if not prefix:
        return None
    _KEYWORDS = ("=", "return", "if ", "for ", "while ", "switch ", "case ", "goto ", "do ")
    if any(tok in prefix for tok in _KEYWORDS):
        return None

    open_idx = raw.find("(", m.start())
    depth, close_idx = 0, None
    for i in range(open_idx, len(raw)):
        if raw[i] == "(":
            depth += 1
        elif raw[i] == ")":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx is None:
        return None

    rest = raw[close_idx + 1 :].strip()
    if rest.startswith(";"):
        kind = "prototype"
    elif rest == "" or rest.startswith("{"):
        kind = "definition"
    else:
        return None

    name = m.group(1)
    sig = raw[: close_idx + 1].strip()
    return name, sig, kind, close_idx


def normalize_sig(sig: str) -> str:
    s = sig.strip()
    changed = True
    while changed:
        changed = False
        new = re.sub(r"^\s*(?:static|inline|extern)\s+", "", s)
        if new != s:
            s, changed = new, True
            continue
        new = re.sub(r"^\s*__attribute__\s*\(\([^\n]*?\)\)\s*", "", s)
        if new != s:
            s, changed = new, True
            continue
    return s.strip()

def params_of(sig: str) -> str:
    return sig[sig.find("(") + 1 : sig.rfind(")")].strip()


def split_params(params: str) -> list[str]:
    if params.strip() in ("", "void"):
        return []
    out: list[str] = []
    depth, cur = 0, []
    for ch in params:
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        out.append(tail)
    return out


def is_simple(sig: str) -> bool:
    p = params_of(sig)
    if p in ("", "void"):
        return True
    if "..." in p or "[" in p or "]" in p or "(*" in p:
        return False
    for part in split_params(p):
        if re.search(r"\b(struct|union)\b", part) and "*" not in part:
            return False
    return True

def default_arg_for(_param: str) -> str:
    """Just so you know this is just to return a default value for an argument"""
    return "0"

def collect_prototypes(lines: list[str]) -> dict[str, str]:
    protos: dict[str, str] = {}

    for line in lines:
        info = extract_signature(line)
        if info is None:
            continue
        name, sig, kind, _ = info
        if kind == "prototype":
            protos[name] = normalize_sig(sig)

    for line in lines:
        info = extract_signature(line)
        if info is None:
            continue
        name, sig, kind, _ = info
        if kind == "definition" and name not in protos:
            protos[name] = normalize_sig(sig)

    return protos
