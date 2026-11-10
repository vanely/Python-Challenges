"""Import `notesql` from the project directory pytest was launched in."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    root = Path.cwd().resolve()
    for entry in (root / "src", root):
        text = str(entry)
        if entry.is_dir() and text not in sys.path:
            sys.path.insert(0, text)
