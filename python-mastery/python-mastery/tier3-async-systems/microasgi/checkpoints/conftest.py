"""Import `microasgi` from the project you launched pytest from.

A src-layout checkout (`src/microasgi`) is preferred. An installed copy also works.
"""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    root = Path.cwd().resolve()
    src = root / "src"
    for entry in (src, root):
        text = str(entry)
        if entry.is_dir() and text not in sys.path:
            sys.path.insert(0, text)
