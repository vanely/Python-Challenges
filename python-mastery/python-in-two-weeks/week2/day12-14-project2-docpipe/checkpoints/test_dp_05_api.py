"""Step 5: the FastAPI service. Spec: steps/05-api.md."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import make_pdf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from docpipe.api import create_app
from docpipe.pipeline import ingest_file
from docpipe.store import Store


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    with Store(path) as s:
        ingest_file(make_pdf(tmp_path / "s.pdf"), s)
    return path


@pytest.fixture
def client(db: Path) -> Iterator[TestClient]:
    with TestClient(create_app(db)) as c:
        yield c


def test_create_app_is_a_factory(db: Path) -> None:
    a, b = create_app(db), create_app(db)
    assert isinstance(a, FastAPI) and a is not b


def test_search(client: TestClient) -> None:
    r = client.get("/search", params={"q": "phonics", "limit": 5})
    assert r.status_code == 200
    hits = r.json()
    assert hits and hits[0]["page_no"] == 1
    assert set(hits[0]) == {"document_id", "path", "page_no", "chunk_index", "score", "snippet"}


@pytest.mark.parametrize(
    "params", [{"q": ""}, {"q": "x", "limit": 0}, {"q": "x", "limit": 51}, {"limit": 5}]
)
def test_search_validation(client: TestClient, params: dict[str, object]) -> None:
    assert client.get("/search", params=params).status_code == 422


def test_documents_list_and_detail(client: TestClient) -> None:
    docs = client.get("/documents").json()
    assert len(docs) == 1 and docs[0]["pages"] == 2
    one = client.get(f"/documents/{docs[0]['id']}")
    assert one.status_code == 200
    body = one.json()
    assert body["chunks"] >= 1
    assert set(body) == {"id", "path", "pages", "chunks", "ingested_at"}


def test_missing_document_is_404_json(client: TestClient) -> None:
    r = client.get("/documents/999")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert "999" in r.json()["detail"]


def test_export_streams_ndjson(client: TestClient) -> None:
    r = client.get("/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")
    rows = [json.loads(line) for line in r.text.splitlines() if line]
    assert rows and [row["chunk_index"] for row in rows] == list(range(len(rows)))


def test_openapi_documents_the_response_models(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "SearchHit" in schemas and "DocumentOut" in schemas


def test_lifespan_opens_and_closes_the_store(db: Path) -> None:
    app = create_app(db)
    with TestClient(app) as c:
        assert c.get("/documents").status_code == 200
        store = app.state.store
    with pytest.raises(sqlite3.ProgrammingError):
        store.list_documents()
