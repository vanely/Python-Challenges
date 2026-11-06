"""Step 2: SQLite + FTS5 storage. Spec: steps/02-store.md."""

from __future__ import annotations

import inspect
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from docpipe.models import Chunk, SearchHit
from docpipe.store import DocumentNotFound, Store


def _doc(store: Store, path: str = "/a.pdf", *texts: str, sha: str = "h1") -> int:
    chunks = [Chunk(page_no=i + 1, index=i, text=t) for i, t in enumerate(texts)]
    return store.replace_document(path, sha, max(len(texts), 1), chunks)


def test_replace_get_and_count(store: Store) -> None:
    doc_id = _doc(store, "/a.pdf", "systematic phonics instruction", "reading fluency")
    d = store.get(doc_id)
    assert (d.path, d.sha256, d.pages) == ("/a.pdf", "h1", 2)
    assert isinstance(d.ingested_at, datetime) and d.ingested_at.tzinfo is not None
    assert store.chunk_count(doc_id) == 2
    assert store.find_by_path("/a.pdf") == d
    assert store.find_by_path("/nope.pdf") is None


def test_get_missing_raises(store: Store) -> None:
    with pytest.raises(DocumentNotFound) as ei:
        store.get(42)
    assert ei.value.doc_id == 42


def test_search_returns_ranked_hits_with_snippets(store: Store) -> None:
    _doc(store, "/a.pdf", "phonics phonics phonics in every line", "unrelated text")
    _doc(store, "/b.pdf", "a single mention of phonics among many other words here")
    hits = store.search("phonics")
    assert all(isinstance(h, SearchHit) for h in hits)
    assert [h.path for h in hits] == ["/a.pdf", "/b.pdf"], "bm25: lower score ranks first"
    assert hits[0].score <= hits[1].score
    assert "[phonics]" in hits[0].snippet
    assert (hits[0].page_no, hits[0].chunk_index) == (1, 0)


def test_search_limit_and_and_semantics(store: Store) -> None:
    for i in range(5):
        _doc(store, f"/{i}.pdf", f"common word number{i}")
    assert len(store.search("common", limit=3)) == 3
    assert [h.path for h in store.search("common number2")] == ["/2.pdf"], "terms are ANDed"


def test_stemming(store: Store) -> None:
    _doc(store, "/a.pdf", "teaching readers to read")
    assert store.search("teach") != []
    assert store.search("readers") != []


@pytest.mark.parametrize(
    "query",
    ['read" OR "x', "NEAR(a b)", "a AND", "-read", "read*", "col:read", '"', "(", "^read", ""],
)
def test_user_input_cannot_break_fts_syntax(store: Store, query: str) -> None:
    _doc(store, "/a.pdf", "teaching readers to read")
    store.search(query)  # must not raise sqlite3.OperationalError


def test_quotes_are_literal_not_operators(store: Store) -> None:
    _doc(store, "/a.pdf", "teaching readers to read")
    assert store.search('read" OR "x') == []


def test_replace_removes_stale_chunks_from_the_index(store: Store) -> None:
    _doc(store, "/a.pdf", "alpha", sha="v1")
    _doc(store, "/a.pdf", "beta", sha="v2")
    assert len(store.list_documents()) == 1
    assert store.search("alpha") == []
    assert len(store.search("beta")) == 1
    assert [r["chunks"] for r in store.stats_rows()] == [1]


def test_replace_is_atomic(store: Store) -> None:
    _doc(store, "/a.pdf", "original", sha="v1")

    def exploding() -> Iterator[Chunk]:
        yield Chunk(1, 0, "half")
        raise RuntimeError("extraction died mid-file")

    with pytest.raises(RuntimeError):
        store.replace_document("/a.pdf", "v2", 1, exploding())
    (doc,) = store.list_documents()
    assert doc.sha256 == "v1", "a failed replace must leave the old version intact"
    assert len(store.search("original")) == 1
    assert store.search("half") == []


def test_foreign_keys_are_enforced(store: Store) -> None:
    conn = store._conn  # type: ignore[attr-defined]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO chunks (document_id, page_no, chunk_index, text, word_count)"
            " VALUES (999, 1, 0, 'x', 1)"
        )


def test_stats_rows_and_iter_chunks(store: Store) -> None:
    _doc(store, "/b.pdf", "one two", "three")
    _doc(store, "/a.pdf")
    rows = store.stats_rows()
    assert [(r["path"], r["chunks"], r["words"]) for r in rows] == [
        ("/a.pdf", 0, 0),
        ("/b.pdf", 2, 3),
    ], "LEFT JOIN: documents with no chunks still appear, with 0 words"
    assert inspect.isgeneratorfunction(Store.iter_chunks)
    out = list(store.iter_chunks())
    assert [(r["path"], r["chunk_index"], r["text"]) for r in out] == [
        ("/b.pdf", 0, "one two"),
        ("/b.pdf", 1, "three"),
    ]
    assert {"document_id", "page_no", "word_count"} <= set(out[0])


def test_file_database_persists(tmp_path: Path) -> None:
    db = tmp_path / "docs.db"
    with Store(db) as s:
        _doc(s, "/a.pdf", "persisted words")
    with Store(db) as s:
        assert len(s.search("persisted")) == 1


def test_context_manager_closes(tmp_path: Path) -> None:
    with Store(tmp_path / "x.db") as s:
        pass
    with pytest.raises(sqlite3.ProgrammingError):
        s.list_documents()
