from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docpipe.api import create_app
from docpipe.pipeline import ingest_file
from docpipe.store import Store
from tests.conftest import make_pdf


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db = tmp_path / "t.db"
    with Store(db) as s:
        ingest_file(make_pdf(tmp_path / "s.pdf"), s)
    with TestClient(create_app(db)) as c:
        yield c


def test_search(client: TestClient) -> None:
    r = client.get("/search", params={"q": "phonics", "limit": 5})
    assert r.status_code == 200
    hits = r.json()
    assert hits and hits[0]["page_no"] == 1


def test_search_validation(client: TestClient) -> None:
    assert client.get("/search", params={"q": ""}).status_code == 422
    assert client.get("/search", params={"q": "x", "limit": 999}).status_code == 422


def test_documents(client: TestClient) -> None:
    docs = client.get("/documents").json()
    assert len(docs) == 1 and docs[0]["pages"] == 2
    one = client.get(f"/documents/{docs[0]['id']}").json()
    assert one["chunks"] >= 1
    assert client.get("/documents/999").status_code == 404


def test_export_ndjson(client: TestClient) -> None:
    r = client.get("/export")
    lines = [ln for ln in r.text.splitlines() if ln]
    assert r.headers["content-type"].startswith("application/x-ndjson")
    assert len(lines) >= 1
