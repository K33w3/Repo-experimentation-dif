#!/usr/bin/env python3
"""
Binary analyzer entry point.

Delegates to :mod:`analyzer.main`.  This thin wrapper preserves the
original script name so that the shell runner can invoke it unchanged.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so ``analyzer`` is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyzer.main import main  # noqa: E402

if __name__ == "__main__":
    main()
