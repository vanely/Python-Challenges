from collections.abc import Iterator

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
