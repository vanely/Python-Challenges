# Step 2 — SQLite storage with a full-text index

**Time:** ~3 h · **Checkpoint:** `uv run pytest ../checkpoints/test_dp_02_store.py`

## What you'll have at the end

`store.py` with a `Store` that:
- owns one SQLite connection and closes it reliably;
- keeps a full-text index in sync with the `chunks` table **automatically**, using triggers;
- replaces a document and all its chunks **atomically**: a failure halfway leaves the old version intact;
- searches with relevance ranking and highlighted snippets, and can't be broken by user input.

## Concepts

### `sqlite3` essentials

```python
conn = sqlite3.connect("docs.db")          # file is created if missing; ":memory:" for tests
conn.row_factory = sqlite3.Row             # rows support row["col"] and dict(row)
conn.execute("SELECT * FROM t WHERE id = ?", (doc_id,))     # ALWAYS placeholders
conn.executemany("INSERT INTO t VALUES (?, ?)", rows)       # rows can be a generator
```

- **Placeholders, never f-strings.** `?` sends the value separately from the SQL text, so SQL injection is impossible. The second argument must be a tuple: `(doc_id,)` with the comma.
- `executemany` accepts any iterable and pulls from it lazily. Pass it a generator and rows stream into the database.

### Transactions: `with conn:` commits; it does not close

```python
with conn:                 # BEGIN (implicitly, on the first write)
    conn.execute("DELETE ...")
    conn.execute("INSERT ...")
# normal exit → COMMIT;  exception → ROLLBACK (and the exception propagates)
```

This is the most misunderstood API in the standard library. The connection's context manager manages a **transaction**, and the connection stays open afterwards. Closing is your job, which is why `Store` is its own context manager with `__exit__` calling `close()`.

Atomic replace falls out of this. Delete the old document, insert the new one, insert all its chunks, all inside one `with conn:`. If chunk extraction raises halfway (the chunks are a generator, so extraction runs *during* `executemany`), the whole thing rolls back, including the delete.

### Foreign keys are off by default, per connection

`REFERENCES documents(id) ON DELETE CASCADE` does **nothing** in SQLite unless you run `PRAGMA foreign_keys = ON` on every new connection. It's a per-connection setting, kept off by default for backwards compatibility. Forget it, and deleting a document leaves orphaned chunks that are still in the search index.

### FTS5 and "external content" tables

FTS5 is SQLite's full-text search engine. It's a *virtual table* backed by an inverted index: for each term, it stores which rows contain it.

```sql
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    text, content='chunks', content_rowid='id', tokenize='porter unicode61'
);
```

- `content='chunks'`: an **external content** table. The index refers to rows of `chunks` by `id` instead of storing a second copy of every chunk's text.
- `tokenize='porter unicode61'`: split on Unicode word boundaries, case-fold, then apply the Porter **stemmer**, so `teaching`, `teaches` and `teach` all index as `teach`.
- The catch: FTS5 doesn't watch `chunks`. **You** must tell it about every insert and delete, and **triggers** do that automatically:

```sql
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
```

The odd-looking delete is FTS5's "delete command": insert a row whose first column is the table's own name and the value `'delete'`, along with the **old** text, so FTS knows which terms to remove. Rows deleted by `ON DELETE CASCADE` fire these triggers too, so deleting a document cleans the index.

### Ranking and snippets

```sql
SELECT ..., bm25(chunks_fts) AS score,
       snippet(chunks_fts, 0, '[', ']', '…', 12) AS snippet
FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid
WHERE chunks_fts MATCH ?
ORDER BY score
```

- `bm25()` is the standard relevance formula. It rewards rare terms and repeated matches, and normalises by length. FTS5 returns it **negated**, so **lower is better** and you `ORDER BY score` ascending.
- `snippet(table, column, open, close, ellipsis, max_tokens)` returns a short excerpt with matches wrapped in `[`…`]`.

### MATCH has its own query language, so quote user input

`MATCH` interprets `OR`, `AND`, `NOT`, `NEAR(...)`, `*` (prefix), `^` (start of column), `col:` (column filter), parentheses and quotes. A user typing `C++ (draft` gets an `sqlite3.OperationalError: fts5: syntax error`. A user typing `x OR y` changes your query's meaning. Placeholders don't help here: the *value* is itself a query in a mini-language.

The fix is to turn every whitespace-separated term into an FTS5 **string**: wrap it in double quotes and double any embedded quote (`"` → `""`). Terms separated by spaces are implicitly ANDed. An empty query becomes `""`, which matches nothing, instead of raising an error.

### `check_same_thread`

By default, a `sqlite3` connection refuses use from any thread other than its creator. FastAPI (step 5) runs `def` handlers in a thread pool, so the API's single connection would be refused. `check_same_thread=False` lifts the check. That's safe here because SQLite built in "serialized" mode (`sqlite3.threadsafety == 3`, the norm) locks around each call, and the API only reads. Two threads *writing* through one connection would share one transaction, which is a different design (a connection per request, or a pool).

## Build

### 1. Schema and lifecycle

```python
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
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)

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
```

- The connection attribute must be named `_conn`; one checkpoint inspects it to confirm foreign keys are on.
- `IF NOT EXISTS` everywhere makes opening an existing database a no-op. This is a poor man's migration story. Fine here; Stage 2 shows the real one.
- `journal_mode = WAL` lets readers keep reading while a writer writes. On `:memory:` it's silently ignored.
- `ingested_at` is stored as ISO-8601 text. SQLite has no datetime type, and ISO strings sort correctly.

### 2. Documents

```python
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
```

And at module level:

```python
def _doc(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"],
        path=row["path"],
        sha256=row["sha256"],
        pages=row["pages"],
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
    )
```

- `get` raises and `find_by_path` returns `None`, and that difference is deliberate. A missing id is an error (someone asked for a specific thing), while a missing path is a normal question ("have I seen this file?").
- `assert doc_id is not None` narrows `int | None` to `int` for mypy. `lastrowid` is only `None` before any insert.
- `return` inside `with self._conn:` still commits: the `with` exits normally.

### 3. Bulk reads

```python
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
```

`LEFT JOIN` + `count(c.id)` (not `count(*)`) + `coalesce(sum(...), 0)`: a document with no chunks (a fully scanned PDF) still appears, with 0 chunks and 0 words. With `count(*)` it would show 1 chunk, and with `sum` alone, `None` words.

### 4. Your turn: `search` and `_fts_query`

```python
    def search(self, query: str, limit: int = 10) -> list[SearchHit]: ...

def _fts_query(q: str) -> str: ...
```

- `search` runs the ranking query from Concepts (`bm25`, `snippet` with `[`/`]`/`…`/12 tokens, joined to `chunks` and `documents`, `ORDER BY score`, `LIMIT ?`) and returns `SearchHit`s. The selected column names must match `SearchHit`'s fields, so you can build each one with `SearchHit(**dict(row))`.
- `_fts_query` turns user input into a safe FTS5 expression: each whitespace-separated term becomes a double-quoted string with embedded `"` doubled, and the terms are joined by spaces. Empty input gives `'""'`.
- None of these inputs may raise: `'read" OR "x'`, `NEAR(a b)`, `a AND`, `-read`, `read*`, `col:read`, `"`, `(`, `^read`, and the empty string.

<details><summary>Hint: why quoting defuses operators</summary>

Inside an FTS5 string, `OR` is just the word "or", `*` is just punctuation (which the tokenizer drops), and `(` is nothing. Only an unbalanced `"` could escape the string, and doubling handles that. `'read" OR "x'` splits into `read"`, `OR` and `"x`, which become `"read"""`, `"OR"` and `"""x"`: three literal terms ANDed together. The tokenizer drops the quote characters inside them, so it's a plain search for chunks containing the words `read`, `or` and `x`. `OR` is no longer an operator.
</details>

### 5. Poke at it

```bash
uv run python
>>> from docpipe.store import Store; from docpipe.models import Chunk
>>> s = Store()
>>> s.replace_document("/a.pdf", "x", 1, [Chunk(1, 0, "Teaching phonics to early readers")])
>>> s.search("teach")
>>> s._conn.execute("SELECT * FROM chunks_fts WHERE chunks_fts MATCH 'reader'").fetchall()
>>> s._conn.execute("SELECT * FROM chunks_fts WHERE chunks_fts MATCH 'C++ (draft'")   # see the raw error
```

## Checkpoint

```bash
uv run pytest ../checkpoints/test_dp_02_store.py
uv run mypy src && uv run ruff check .
```

## Pitfalls

- **Expecting `with conn:` to close.** Then you leak connections (and on Windows, file locks) until garbage collection.
- **Forgetting `PRAGMA foreign_keys = ON`.** Nothing fails. Orphans accumulate silently.
- **An FTS table with its own copy of the text and no triggers.** Search then returns deleted chunks, or misses new ones. The FTS index is a derived structure, and something must keep it in sync.
- **`f"... MATCH '{q}'"`.** That's SQL injection *and* FTS injection at once.
- **Assuming `chunks` is a list.** `replace_document` accepts any iterable, including a generator that raises partway through. The checkpoint's atomicity test passes exactly that. If the insert consumes it inside the transaction, the rollback covers the earlier delete. Step 3's caller happens to pass a list, but the store shouldn't depend on that.

## Explain it back

1. What exactly does `with conn:` do on success, on exception, and to the connection itself?
2. Walk through what happens to `chunks_fts` when `replace_document` deletes a document that has 5 chunks.
3. Why doesn't a `?` placeholder protect the `MATCH` argument from user syntax?
4. Why is `bm25()` sorted ascending?
5. In `stats_rows`, what would `count(*)` report for a document with no chunks, and why?
6. Why is `check_same_thread=False` acceptable for this API but not for a write-heavy one?
