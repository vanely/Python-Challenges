# Step 2 — Routes, settings, and the 404

**Checkpoint:** `uv run pytest ../checkpoints`

## Concepts

A `def` route that calls the repo runs in FastAPI's thread pool. That's the right choice: the repo is synchronous. `async def` plus a blocking call would stall every other request.

`NoteNotFound` stays a domain error. One `@app.exception_handler` turns it into JSON `{"detail": "...", "id": 999}` with status 404. The tests check both keys.

`Annotated[NoteRepo, Depends(get_repo)]` is the injection point. Tests replace `get_repo` with `app.dependency_overrides` so each test gets an empty repo. A module-level `MemoryRepo()` without that override leaks notes between tests.

`BaseSettings` with `env_prefix="NOTES_"` reads `NOTES_APP_NAME` and `NOTES_MAX_PAGE`. The list route's `limit` uses `Query(ge=1, le=settings.max_page)`, so `limit=999` is a 422 when the default cap is 100.

## Build

`app/settings.py`: `Settings(BaseSettings)` with `app_name: str = "Notes API"` and `max_page: int = 100`, prefix `NOTES_`. A module-level `settings = Settings()`.

`app/deps.py`: one `MemoryRepo`, `get_repo() -> NoteRepo`, and `Repo = Annotated[NoteRepo, Depends(get_repo)]`.

`app/main.py`: `FastAPI(title=settings.app_name)`, include the router, the `NoteNotFound` handler, and `GET /health` → `{"status": "ok"}`.

## Your turn: `app/routes.py`

| Method | Path | Behaviour |
|---|---|---|
| GET | `/notes` | `limit` (default 20, 1…`settings.max_page`), `offset` (default 0, ≥0), optional `tag`. Returns `Page[NoteOut]`. |
| POST | `/notes` | Body `NoteIn`, status 201, returns `NoteOut`. |
| GET | `/notes/{note_id}` | `NoteOut`, or the 404 handler. |
| PATCH | `/notes/{note_id}` | Body `NoteUpdate`. Pass `model_dump(exclude_unset=True)` to `repo.update`. A `ValidationError` from the repo's re-check becomes `RequestValidationError` so the client still sees a 422. |
| DELETE | `/notes/{note_id}` | Status 204, no body. |

The router prefix is `/notes`.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_repo.py ../checkpoints/test_api.py
uv run mypy app && uv run ruff check app
```

## Explain it back

1. What does `dependency_overrides` replace, and what leaks if you forget it?
2. Why is the 404 an exception handler rather than a `try/except` in every route?
3. Who rejects `limit=999`, and what status does the client get?
