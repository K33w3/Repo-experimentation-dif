#!/usr/bin/env python3
"""
We select the attributes here, which functions to instrument, and assign the attributes.
"""
import csv
import random
from .signatures import is_simple


def select_targets(
    protos: dict[str, str],
    rng: random.Random,
    min_targets: int,
    max_targets: int,
) -> list[str]:
    candidates = sorted(protos.keys(), key=lambda n: int(n.split("_")[1]))
    simple = [c for c in candidates if is_simple(protos[c])]
    if not simple:
        return []

    k = min(
        len(simple),
        rng.randint(min(min_targets, len(simple)), min(max_targets, len(simple))),
    )
    return rng.sample(simple, k)


_WEIRD_ATTRS = ("none", "hidden", "used")


def assign_attributes(
    targets: list[str],
    protos: dict[str, str],
    rng: random.Random,
) -> list[dict]:
    rows: list[dict] = []
    for name in targets:
        roll = rng.random()
        if roll < 0.25:
            func_attr, call_mode, expected = "nocf_check", "nocf_ptr", "NO"
        elif roll < 0.35:
            func_attr, call_mode, expected = "cf_check", "plain", "YES"
        else:
            func_attr = "none"
            call_mode = "nocf_ptr" if rng.random() < 0.35 else "plain"
            expected = "ANY" if call_mode == "nocf_ptr" else "YES"

        rows.append({
            "name": name,
            "prototype": protos[name],
            "func_attr": func_attr,
            "call_mode": call_mode,
            "weird_attr": rng.choice(_WEIRD_ATTRS),
            "expected_endbr": expected,
        })
    return rows

def build_attrs(row: dict) -> str:
    out = ["__attribute__((noinline))"]
    if row["func_attr"] == "nocf_check":
        out.append("__attribute__((nocf_check))")
    elif row["func_attr"] == "cf_check":
        out.append("__attribute__((cf_check))")
    if row["weird_attr"] == "hidden":
        out.append('__attribute__((visibility("hidden")))')
    elif row["weird_attr"] == "used":
        out.append("__attribute__((used))")
    return " ".join(out)


def rewrite_source(lines: list[str], row_map: dict[str, dict]) -> list[str]:
    from .signatures import extract_signature

    for idx, line in enumerate(lines):
        info = extract_signature(line)
        if info is None:
            continue
        name, _, kind, close_idx = info
        if name not in row_map:
            continue

        row = row_map[name]
        attrs = build_attrs(row)
        raw = line.rstrip("\n")
        rest = raw[close_idx + 1 :]
        base_sig = row["prototype"]

        if kind == "prototype":
            lines[idx] = f"{attrs} {base_sig};\n"
        else:
            lines[idx] = f"{attrs} {base_sig}{rest}\n"

    return lines

def write_plan(rows: list[dict], plan_path: str) -> None:
    with open(plan_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "function", "prototype", "func_attr",
            "call_mode", "weird_attr", "expected_endbr",
        ])
        for row in rows:
            w.writerow([
                row["name"], row["prototype"], row["func_attr"],
                row["call_mode"], row["weird_attr"], row["expected_endbr"],
            ])

def write_targets(rows: list[dict], targets_path: str) -> None:
    with open(targets_path, "w") as f:
        for row in rows:
            f.write(row["name"] + "\n")
