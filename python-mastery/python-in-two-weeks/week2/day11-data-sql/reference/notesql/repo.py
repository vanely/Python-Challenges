"""SQLite notes store. Same shape Day 10's MemoryRepo had, with a tags table."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (note_id, tag)
);
"""


class NoteNotFound(Exception):
    def __init__(self, note_id: int) -> None:
        super().__init__(f"note {note_id} not found")
        self.note_id = note_id


def _tags(raw: list[str] | None) -> list[str]:
    return sorted({t.strip().lower() for t in (raw or []) if t.strip()})


class SqliteRepo:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def create(self, title: str, body: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        clean = _tags(tags)
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO notes (title, body, created_at) VALUES (?, ?, ?)",
                (title, body, datetime.now(UTC).isoformat()),
            )
            note_id = int(cur.lastrowid or 0)
            self._conn.executemany(
                "INSERT INTO note_tags (note_id, tag) VALUES (?, ?)",
                ((note_id, tag) for tag in clean),
            )
        return self.get(note_id)

    def get(self, note_id: int) -> dict[str, Any]:
        row = self._conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if row is None:
            raise NoteNotFound(note_id)
        tags = [
            r["tag"]
            for r in self._conn.execute(
                "SELECT tag FROM note_tags WHERE note_id = ? ORDER BY tag", (note_id,)
            )
        ]
        return {
            "id": row["id"],
            "title": row["title"],
            "body": row["body"],
            "tags": tags,
            "created_at": row["created_at"],
        }

    def list(
        self, *, limit: int, offset: int, tag: str | None
    ) -> tuple[list[dict[str, Any]], int]:
        where = ""
        params: tuple[object, ...] = ()
        if tag is not None:
            where = (
                " WHERE id IN (SELECT note_id FROM note_tags WHERE tag = ?)"
            )
            params = (tag,)
        total = int(
            self._conn.execute(f"SELECT count(*) AS n FROM notes{where}", params).fetchone()["n"]
        )
        ids = [
            r["id"]
            for r in self._conn.execute(
                f"SELECT id FROM notes{where} ORDER BY id LIMIT ? OFFSET ?",
                (*params, limit, offset),
            )
        ]
        return [self.get(i) for i in ids], total

    def update(self, note_id: int, changes: dict[str, object]) -> dict[str, Any]:
        current = self.get(note_id)
        title = changes.get("title", current["title"])
        body = changes.get("body", current["body"])
        with self._conn:
            self._conn.execute(
                "UPDATE notes SET title = ?, body = ? WHERE id = ?", (title, body, note_id)
            )
            if "tags" in changes:
                raw = changes["tags"]
                clean = _tags(raw if isinstance(raw, list) else [])
                self._conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
                self._conn.executemany(
                    "INSERT INTO note_tags (note_id, tag) VALUES (?, ?)",
                    ((note_id, tag) for tag in clean),
                )
        return self.get(note_id)

    def delete(self, note_id: int) -> None:
        self.get(note_id)
        with self._conn:
            self._conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
