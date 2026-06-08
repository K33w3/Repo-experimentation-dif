#!/usr/bin/env python3
"""
Harness and plan generator entry point. Usage example:
    python3 generate_harness.py <src> <harness> <plan.csv> <targets.txt> \\
                                <seed> <min_targets> <max_targets>
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generator.harness import emit_harness          
from generator.plan import (                         
    assign_attributes,
    rewrite_source,
    select_targets,
    write_plan,
    write_targets,
)
from generator.signatures import collect_prototypes


def main() -> None:
    src_path     = Path(sys.argv[1])
    harness_path = sys.argv[2]
    plan_path    = sys.argv[3]
    targets_path = sys.argv[4]
    seed         = int(sys.argv[5])
    min_targets  = int(sys.argv[6])
    max_targets  = int(sys.argv[7])

    rng = random.Random(seed)
    lines = src_path.read_text().splitlines(True)

    protos = collect_prototypes(lines)
    if not protos:
        print("no candidate functions", file=sys.stderr)
        sys.exit(2)

    targets = select_targets(protos, rng, min_targets, max_targets)
    if not targets:
        print("no simple candidates", file=sys.stderr)
        sys.exit(3)

    rows = assign_attributes(targets, protos, rng)
    row_map = {r["name"]: r for r in rows}

    rewrite_source(lines, row_map)
    src_path.write_text("".join(lines))

    emit_harness(rows, harness_path)
    write_plan(rows, plan_path)
    write_targets(rows, targets_path)


if __name__ == "__main__":
    main()
