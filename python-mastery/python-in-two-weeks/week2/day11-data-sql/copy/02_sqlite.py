"""Day 11 — sqlite3 the safe way."""
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (note_id, tag)
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, body, content='notes', content_rowid='id');
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row            # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


with closing(connect()) as conn:
    # `with conn:` = transaction: commit on success, rollback on exception. Does NOT close.
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (title, body, created_at) VALUES (?, ?, ?)",
            ("First", "hello world", datetime.now(UTC).isoformat()),
        )
        note_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO note_tags (note_id, tag) VALUES (:id, :tag)",
            [{"id": note_id, "tag": t} for t in ("intro", "demo")],
        )
        conn.execute("INSERT INTO notes_fts(rowid, title, body) VALUES (?, ?, ?)",
                     (note_id, "First", "hello world"))

    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    print(dict(row))
    print([r["tag"] for r in conn.execute("SELECT tag FROM note_tags WHERE note_id = ?", (note_id,))])

    # NEVER: conn.execute(f"SELECT ... WHERE title = '{user_input}'")
    user_input = "x' OR 1=1 --"
    print(conn.execute("SELECT count(*) FROM notes WHERE title = ?", (user_input,)).fetchone()[0])

    # rollback on error
    try:
        with conn:
            conn.execute("INSERT INTO notes (title, body, created_at) VALUES (?, ?, ?)", ("tmp", "", "t"))
            raise RuntimeError("abort")
    except RuntimeError:
        pass
    print("notes after rollback:", conn.execute("SELECT count(*) FROM notes").fetchone()[0])

    # full-text search
    hits = conn.execute("SELECT rowid, title FROM notes_fts WHERE notes_fts MATCH ?", ("hello",)).fetchall()
    print([dict(h) for h in hits])

    # cascade
    with conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    print("tags left:", conn.execute("SELECT count(*) FROM note_tags").fetchone()[0])
