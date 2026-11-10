"""Learner modules in this folder win. CI sets CHECK_REFERENCE=1 to import reference/."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_project = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project))
if os.environ.get("CHECK_REFERENCE") == "1":
    sys.path.insert(0, str(_project / "reference"))
