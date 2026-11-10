"""Import lab modules from this folder, and fall back to reference/ for v1–v3."""

from __future__ import annotations

import sys
from pathlib import Path

_lab = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_lab))
_ref = str(_lab / "reference")
if _ref not in sys.path:
    sys.path.append(_ref)
