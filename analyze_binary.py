#!/usr/bin/env python3
"""
Binary analyzer entry point.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyzer.main import main

if __name__ == "__main__":
    main()
