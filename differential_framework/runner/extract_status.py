#!/usr/bin/env python3
"""
Extract per-target ENDBR status for cross-config differential analysis.
"""
import json
import sys


def main() -> None:
    with open(sys.argv[1]) as f:
        d = json.load(f)

    for t in d["target_status"]:
        print(f"DIFF\t{t['name']}\t{t['status']}")


if __name__ == "__main__":
    main()
