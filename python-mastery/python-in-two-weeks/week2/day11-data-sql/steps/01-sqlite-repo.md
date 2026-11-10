# Step 1 — `SqliteRepo`

**Checkpoint:** `uv run pytest ../checkpoints/test_repo_and_report.py -k "not summarise"`

Day 10's `MemoryRepo` disappears when the process does. This step keeps the same operations and puts them in SQLite. The checkpoint talks to `notesql.SqliteRepo` directly, so you don't have to wire it into FastAPI until you're done.

## Concepts

You typed `copy/02_sqlite.py` today. The parts that matter here:

- `with conn:` commits on success and rolls back on exception. It does not close the connection.
- `?` placeholders. The tag filter is a value, not a piece of SQL text.
- `PRAGMA foreign_keys = ON` on every connection, or `ON DELETE CASCADE` does nothing.
- One note, many tags: a `note_tags` table, not a comma-separated column. Deleting the note deletes its tags only because the foreign key is on and the pragma ran.

## Build

```bash
cd week2/day11-data-sql
uv init --name sqlnotes
cd sqlnotes
uv add polars
uv add --dev pytest
```

Package layout: `notesql/__init__.py` re-exports `SqliteRepo`, `NoteNotFound`, and `summarise`.

## Your turn

`notesql/repo.py`:

```python
class NoteNotFound(Exception): ...   # .note_id
class SqliteRepo:
    def __init__(self, path: str = ":memory:") -> None: ...
    def create(self, title: str, body: str = "", tags: list[str] | None = None) -> dict: ...
    def get(self, note_id: int) -> dict: ...
    def list(self, *, limit: int, offset: int, tag: str | None) -> tuple[list[dict], int]: ...
    def update(self, note_id: int, changes: dict[str, object]) -> dict: ...
    def delete(self, note_id: int) -> None: ...
    def close(self) -> None: ...
```

Each note dict has `id`, `title`, `body`, `tags`, `created_at`.

- Tags are stripped, lowercased, de-duplicated, and sorted. Empty strings disappear.
- `created_at` is an aware ISO timestamp.
- `list` returns the page and the **filtered** total. Order is by `id`. `tag="even"` only counts notes that have that tag.
- `update` changes `title` and `body` only when those keys are present. When `tags` is present, it replaces the whole set.
- `get` and `delete` raise `NoteNotFound` for a missing id. After `delete`, a tag filter no longer sees that note's tags.
- `create` / `update` / `delete` each run in one transaction.

Tables: `notes(id, title, body, created_at)` and `note_tags(note_id, tag)` with `REFERENCES notes(id) ON DELETE CASCADE` and a primary key of `(note_id, tag)`.

## Explain it back

1. What does `with conn:` commit, and what does it leave open?
2. Why is the foreign-key pragma per connection?
