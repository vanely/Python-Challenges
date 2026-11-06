# Step 5 — The search API

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/test_dp_05_api.py`, then `uv run pytest ../checkpoints` for everything.

## What you'll have at the end

`api.py` and a working `docpipe serve`, with:
- `GET /search?q=&limit=` returning validated, documented `SearchHit` JSON;
- `GET /documents` and `GET /documents/{id}`, where a missing id is a clean JSON 404;
- `GET /export` streaming every chunk as NDJSON, constant memory however big the corpus is;
- interactive docs at `/docs`, for free.

Day 10 built a FastAPI app with an in-memory repo. This is the same framework on top of the store you built, and it adds an app factory, a lifespan and streaming.

## Concepts

### App factory: `create_app(db_path)`

A module-level `app = FastAPI()` that opens `docs.db` at import time means:
- tests can't point it at a temp database;
- importing the module has side effects;
- two apps can't coexist.

A **factory** takes configuration as arguments and returns a fresh app. Tests call `create_app(tmp_db)`, and the CLI calls `create_app(db)`.

### Lifespan: resources that live as long as the app

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.store = Store(db_path)     # startup
    try:
        yield                            # the app serves requests here
    finally:
        app.state.store.close()          # shutdown
```

- The code before `yield` runs once at startup and the code after it once at shutdown.
- `app.state` is a free-form namespace for app-wide objects.
- This replaces the deprecated `@app.on_event("startup")`.
- `TestClient` only runs the lifespan when used **as a context manager** (`with TestClient(app) as c:`). Without the `with`, `app.state.store` doesn't exist and every request fails with `AttributeError`.

### Dependencies

```python
def get_store(request: Request) -> Store:
    return request.app.state.store

StoreDep = Annotated[Store, Depends(get_store)]
```

A route that declares `store: StoreDep` gets the store injected. The route doesn't know where the store comes from, and a test can swap it with `app.dependency_overrides[get_store] = ...`. `Annotated` aliases keep signatures short and consistent.

### Validation at the boundary

`q: Annotated[str, Query(min_length=1)]` and `limit: Annotated[int, Query(ge=1, le=50)] = 10`:
- FastAPI rejects `q=""`, a missing `q`, `limit=0` and `limit=51` with **422** and a JSON explanation, before your code runs.
- The return annotation `-> list[SearchHit]` validates and serialises the output and documents it in `/openapi.json`. That's why `SearchHit` is a Pydantic model and `Chunk` isn't (step 1, question 6).

### Mapping domain errors to HTTP

`store.get` raises `DocumentNotFound`, a domain error that knows nothing about HTTP. One `@app.exception_handler(DocumentNotFound)` turns it into a 404 **for every route**. That's better than `try/except` → `HTTPException` copied into each handler, and better than the store raising `HTTPException` (which would make the store depend on FastAPI).

### `def` vs `async def` routes

The store is synchronous `sqlite3`. A **`def`** route runs in FastAPI's thread pool, so a slow query doesn't block the event loop. The same blocking call in an `async def` route would freeze every other request while it runs. Rule of thumb: blocking I/O means `def`, and `async def` is only for awaiting. Thread-pool routes are also why step 2 opened the connection with `check_same_thread=False`.

### Streaming

`StreamingResponse(generator, media_type="application/x-ndjson")` sends each yielded string as it's produced. Memory stays at one row whatever the corpus size, and the client starts receiving immediately. A sync generator is iterated in the thread pool, for the same reason as `def` routes.

### Why this file has no `from __future__ import annotations`

FastAPI reads your route signatures at runtime and evaluates any string annotations against the **module's globals**. Every name used in this file's annotations is a module-level import, so the future import would actually work. But the routes live *inside* `create_app`. The day you annotate a route with something defined inside that function (a local model, a local `Annotated` alias), a stringified annotation can't find it and the app fails at startup with a confusing error. Leaving the import out of FastAPI modules removes the trap.

## Build

### 1. `src/docpipe/api.py`, minus three pieces

This replaces step 4's placeholder.

```python
"""FastAPI app. Store opened for the app's lifetime via lifespan."""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from docpipe.models import DocumentOut, SearchHit
from docpipe.store import DocumentNotFound, Store


def get_store(request: Request) -> Store:
    store: Store = request.app.state.store
    return store


StoreDep = Annotated[Store, Depends(get_store)]


def create_app(db_path: Path | str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.store = Store(db_path)
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(title="docpipe", lifespan=lifespan)

    # YOUR TURN (a): exception handler for DocumentNotFound

    @app.get("/search")
    def search(
        store: StoreDep,
        q: Annotated[str, Query(min_length=1)],
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> list[SearchHit]:
        return store.search(q, limit)

    @app.get("/documents")
    def documents(store: StoreDep) -> list[DocumentOut]:
        return [_out(store, d.id) for d in store.list_documents()]

    # YOUR TURN (b): GET /documents/{doc_id}
    # YOUR TURN (c): GET /export

    return app


def _out(store: Store, doc_id: int) -> DocumentOut:
    d = store.get(doc_id)
    return DocumentOut(
        id=d.id,
        path=d.path,
        pages=d.pages,
        chunks=store.chunk_count(d.id),
        ingested_at=d.ingested_at,
    )
```

- `store: Store = request.app.state.store` with an explicit annotation: `app.state` is untyped (`Any`), and the annotation stops `Any` from spreading through every route.
- Parameter order in `search`: `store` and `q` have no defaults, so they come before `limit`. That's Python's rule, not FastAPI's.
- `_out` is shared by the list and detail routes. It's N+1 queries (one `chunk_count` per document), fine for hundreds of documents. Explain-it-back question 6 asks what you'd do at 100 000.

### 2. Your turn

**(a)** An exception handler for `DocumentNotFound`: status **404**, a JSON body `{"detail": "<message>"}` whose message contains the id. `DocumentNotFound`'s `str()` already says `document 999 not found`.

**(b)** `GET /documents/{doc_id}` returns one `DocumentOut`. The path parameter is an `int`, so `/documents/abc` is a 422 for free. A missing id must hit your handler from (a); don't catch it in the route.

**(c)** `GET /export` streams `store.iter_chunks()` as NDJSON: one `json.dumps(row)` per line, a trailing `"\n"` on each, media type `application/x-ndjson`.

<details><summary>Hint: handler signature</summary>

`@app.exception_handler(DocumentNotFound)` on an `async def _nf(request: Request, exc: DocumentNotFound) -> JSONResponse`. Return `JSONResponse(status_code=404, content={...})`.
</details>

<details><summary>Hint: streaming</summary>

Define an inner generator `def lines() -> Iterator[str]:` that loops over `store.iter_chunks()` and yields lines, then `return StreamingResponse(lines(), media_type=...)`. The route's return annotation is `StreamingResponse`, which tells FastAPI not to validate or serialise it.
</details>

### 3. Serve it

```bash
uv run docpipe ingest ../samples --db try.db
uv run docpipe serve --db try.db
```

Open http://127.0.0.1:8000/docs and try `/search` with an empty `q`, `limit=99`, `/documents/999` and `/export`. In a second terminal:

```bash
curl -s "localhost:8000/search?q=phonics&limit=2"
curl -si localhost:8000/documents/999
curl -sN localhost:8000/export | head -3
```

Ctrl+C stops uvicorn, which runs the lifespan shutdown, so the store closes.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_dp_05_api.py
uv run pytest ../checkpoints                 # all five steps
uv run mypy src && uv run ruff check .
```

## Finish the project

1. All checkpoints pass, mypy and ruff are clean, and every "Explain it back" in `NOTES.md` is answered.
2. Write `tests/` of your own for one thing the checkpoints don't cover. Some ideas:
   - `chunk_text` on text with Windows line endings;
   - search ranking order;
   - `export` on an empty database.
3. **Now** open `reference/docpipe/` and diff it file by file. For each difference, note in `NOTES.md` which version is better and why. Sometimes it will be yours.

## Pitfalls

- **`TestClient(app)` without `with`.** The lifespan never runs, so there's no store.
- **`async def` routes calling sqlite.** It works on your machine with one user, and stalls every other request under load.
- **Raising `HTTPException` inside `Store`.** The storage layer then depends on the web framework, and the CLI can't use it cleanly.
- **Returning a `list` from `/export`.** That materialises the corpus and defeats the point.
- **A per-request store dependency with `yield` combined with streaming.** From 0.106 to 0.117, FastAPI ran a `yield` dependency's cleanup *before* sending the response, so a `StreamingResponse` found its database session already closed. 0.118 moved cleanup to after the response, and 0.121 added `Depends(..., scope="function")` for the early-close behaviour. You'll meet both in real codebases. The app-lifetime store here sidesteps the question.

## Explain it back

1. Why a `create_app` factory instead of a module-level `app`? Name two concrete problems it solves.
2. What runs when, in the lifespan, and what breaks if a test uses `TestClient(app)` without `with`?
3. Why are the routes `def` and not `async def`, and how does that connect to `check_same_thread=False`?
4. Why an exception handler instead of catching `DocumentNotFound` in the route?
5. Who rejects `limit=51`, and what status and body does the client get?
6. `/documents` does one `chunk_count` query per document. Rewrite it as one query, in words or SQL.
7. When exactly would `from __future__ import annotations` break this file?
