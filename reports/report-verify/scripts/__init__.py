"""Read-only report verification with repository-level shared data access."""

__version__ = "1.0.0"

import sys
from pathlib import Path


REPORTS_ROOT = Path(__file__).resolve().parents[2]
if str(REPORTS_ROOT) not in sys.path:
    sys.path.insert(0, str(REPORTS_ROOT))
