#!/usr/bin/env python3
"""
Extras generator entry point.

Usage::

    python3 generate_extras.py <output.c> <seed>

Delegates to :mod:`generator.extras`.  This thin wrapper preserves the
original script name so that the shell runner can invoke it unchanged.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generator.extras import generate_extras  # noqa: E402

if __name__ == "__main__":
    generate_extras(out_path=sys.argv[1], seed=int(sys.argv[2]))
