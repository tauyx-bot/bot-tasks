#!/usr/bin/env python3
"""Executable entry point for skill and command-line use."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_ROOT = PROJECT_ROOT.parent
if str(REPORTS_ROOT) not in sys.path:
    sys.path.insert(0, str(REPORTS_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
