"""SQLite storage with FTS5. `Store` is a context manager; writes happen in transactions."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from docpipe.models import Chunk, Document, SearchHit

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    sha256      TEXT NOT NULL,
    pages       INTEGER NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no     INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    word_count  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(document_id, chunk_index);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, content='chunks', content_rowid='id', tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
"""


class DocumentNotFound(Exception):
    def __init__(self, doc_id: int) -> None:
        super().__init__(f"document {doc_id} not found")
        self.doc_id = doc_id


class Store:
    def __init__(self, path: Path | str = ":memory:") -> None:
        # check_same_thread=False: FastAPI runs sync handlers in a threadpool. Safe here
        # because SQLite serialises access internally and we never share a cursor.
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)

    # --- lifecycle ---------------------------------------------------------------
    def __enter__(self) -> Store:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # --- documents --------------------------------------------------------------------
    def find_by_path(self, path: str) -> Document | None:
        row = self._conn.execute("SELECT * FROM documents WHERE path = ?", (path,)).fetchone()
        return _doc(row) if row else None

    def get(self, doc_id: int) -> Document:
        row = self._conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if row is None:
            raise DocumentNotFound(doc_id)
        return _doc(row)

    def list_documents(self) -> list[Document]:
        rows = self._conn.execute("SELECT * FROM documents ORDER BY path").fetchall()
        return [_doc(r) for r in rows]

    def replace_document(self, path: str, sha256: str, pages: int, chunks: Iterable[Chunk]) -> int:
        """Insert or replace a document and all its chunks in one transaction."""
        with self._conn:
            self._conn.execute("DELETE FROM documents WHERE path = ?", (path,))  # cascades
            cur = self._conn.execute(
                "INSERT INTO documents (path, sha256, pages, ingested_at) VALUES (?, ?, ?, ?)",
                (path, sha256, pages, datetime.now(UTC).isoformat()),
            )
            doc_id = cur.lastrowid
            assert doc_id is not None
            self._conn.executemany(
                "INSERT INTO chunks (document_id, page_no, chunk_index, text, word_count)"
                " VALUES (?, ?, ?, ?, ?)",
                ((doc_id, c.page_no, c.index, c.text, c.word_count) for c in chunks),
            )
            return doc_id

    def chunk_count(self, doc_id: int) -> int:
        row = self._conn.execute(
            "SELECT count(*) AS n FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchone()
        return int(row["n"])

    # --- search -------------------------------------------------------------------------
    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        sql = """
        SELECT c.document_id, d.path, c.page_no, c.chunk_index,
               bm25(chunks_fts) AS score,
               snippet(chunks_fts, 0, '[', ']', '…', 12) AS snippet
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        JOIN documents d ON d.id = c.document_id
        WHERE chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """
        rows = self._conn.execute(sql, (_fts_query(query), limit)).fetchall()
        return [SearchHit(**dict(r)) for r in rows]

    # --- bulk reads -----------------------------------------------------------------------
    def iter_chunks(self) -> Iterator[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT c.id, c.document_id, d.path, c.page_no, c.chunk_index, c.text, c.word_count"
            " FROM chunks c JOIN documents d ON d.id = c.document_id"
            " ORDER BY c.document_id, c.chunk_index"
        )
        for row in cur:  # cursor is an iterator; rows stream
            yield dict(row)

    def stats_rows(self) -> list[dict[str, Any]]:
        sql = """
        SELECT d.id, d.path, d.pages, count(c.id) AS chunks, coalesce(sum(c.word_count), 0) AS words
        FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
        GROUP BY d.id ORDER BY d.path
        """
        return [dict(r) for r in self._conn.execute(sql).fetchall()]


def _doc(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"],
        path=row["path"],
        sha256=row["sha256"],
        pages=row["pages"],
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
    )


def _fts_query(q: str) -> str:
    """Quote each term so user input can't break FTS syntax; AND them together."""
    terms = [t.replace('"', '""') for t in q.split() if t]
    return " ".join(f'"{t}"' for t in terms) or '""'
