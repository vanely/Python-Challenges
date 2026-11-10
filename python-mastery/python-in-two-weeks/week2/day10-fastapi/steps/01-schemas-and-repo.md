# Step 1 — The note contract and an in-memory repo

**Checkpoint:** from your project folder, `uv run pytest ../checkpoints/test_repo.py`

## Concepts

Pydantic validates at the boundary. A dataclass would accept `title=""` and `tags=[" B "]` and you'd find out in a template. `Field(min_length=1)` and a `@field_validator` reject or normalise before any route runs.

The repo is a `Protocol`: `list`, `get`, `create`, `update`, `delete`. Day 11 swaps the storage without touching the routes. `NoteNotFound` is a domain error. It carries `note_id`. It does not know about HTTP yet.

## Build

Create the project:

```bash
cd week2/day10-fastapi
uv init --name notes
cd notes
```

`uv init` writes a `.python-version` of 3.12 because of the pin above this folder. Replace `pyproject.toml` with:

```toml
[project]
name = "notes-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn>=0.30", "pydantic>=2.8", "pydantic-settings>=2.4"]

[dependency-groups]
dev = ["pytest>=8", "httpx2>=2", "ruff>=0.6", "mypy>=1.12"]

[tool.pytest.ini_options]
pythonpath = ["."]
```

`httpx2` is what FastAPI's `TestClient` uses. Then `uv sync`.

### `app/schemas.py`

```python
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    body: str = ""
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("tags")
    @classmethod
    def normalise_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t.strip()})


class NoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = None
    tags: list[str] | None = Field(default=None, max_length=10)


class NoteOut(NoteIn):
    id: int
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


def now() -> datetime:
    return datetime.now(UTC)
```

`extra="forbid"` is why `{"title": "", "nope": 1}` mentions both `title` and `nope` in the 422. `Page` is generic so `Page[NoteOut]` documents the list response.

## Your turn: `app/repo.py`

```python
class NoteNotFound(Exception): ...   # .note_id, message "note {id} not found"
class NoteRepo(Protocol): ...        # list, get, create, update, delete
class MemoryRepo: ...
```

- `create` assigns ids from 1, stamps `created_at` with `now()`, and stores a `NoteOut`.
- `list(*, limit, offset, tag)` returns `(page, total)` where `total` is the count **after** the tag filter and **before** the slice.
- `update(note_id, changes)` applies only the keys in `changes` (`model_dump(exclude_unset=True)` from the route). Re-validate the result through `NoteIn` so tag normalisation still runs. Missing id raises `NoteNotFound`.
- `get` and `delete` raise `NoteNotFound` for an unknown id. `delete` returns `None`.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_repo.py
```

## Explain it back

1. Why is a mutable default `tags: list[str] = []` safe on a Pydantic model and fatal on a dataclass?
2. Why does `update` re-validate through `NoteIn` instead of writing `changes` straight onto the stored model?
