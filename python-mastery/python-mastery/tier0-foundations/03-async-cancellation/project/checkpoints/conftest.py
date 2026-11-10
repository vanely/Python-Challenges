"""Make `import fetchd` resolve to the project you launched pytest from."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    root = str(Path.cwd().resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
