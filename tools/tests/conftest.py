"""Test configuration: make the benchkit package importable from the tools root."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS_ROOT = Path(__file__).resolve().parent.parent
if str(_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOOLS_ROOT))
