import sys
from collections.abc import Iterator
from pathlib import Path

# The app under test is the directory you run pytest from, not this folder.
_root = str(Path.cwd().resolve())
if _root not in sys.path:
    sys.path.insert(0, _root)



import pytest
from fastapi.testclient import TestClient

from app.deps import get_repo
from app.main import app
from app.repo import MemoryRepo


@pytest.fixture
def client() -> Iterator[TestClient]:
    fresh = MemoryRepo()
    app.dependency_overrides[get_repo] = lambda: fresh      # isolate state per test
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
