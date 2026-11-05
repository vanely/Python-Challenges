# Day 10: FastAPI + Pydantic

If you've used Express/Hono/NestJS with zod, this is the closest thing Python has — and it's better-typed than most of them.

## Objectives
- Build a small, typed, tested REST API with FastAPI
- Use Pydantic v2 for runtime validation (the thing type hints don't do)
- Understand dependency injection, routers, and the request lifecycle

## Readings

| Source | Where | Read |
|---|---|---|
| FastAPI tutorial | https://fastapi.tiangolo.com/tutorial/ | First Steps → Path Params → Query Params → Request Body → Response Model → Handling Errors → Dependencies → Bigger Applications (routers) → Testing |
| Pydantic | https://docs.pydantic.dev/latest/concepts/models/ | Models; Fields; Validators; `model_validate` / `model_dump` |
| Pydantic settings | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | `BaseSettings` for env config |
| uvicorn | https://www.uvicorn.org/ | Running, `--reload` |
| Starlette TestClient | https://www.starlette.io/testclient/ | All (short) |
| Source | `fastapi/routing.py` → `APIRoute.__init__` and `get_request_handler` | See how the signature is introspected into validation |

## Reading summaries

### Pydantic v2
- `class User(BaseModel): id: int; email: EmailStr; tags: list[str] = []` — mutable defaults are OK here (Pydantic copies).
- Validation happens on construction: `User(id="1")` coerces to `1`; `User(id="x")` raises `ValidationError` with a structured `.errors()`.
- `model_validate(dict)` / `model_validate_json(str)` in; `model_dump()` / `model_dump_json()` out. `exclude_none`, `by_alias`.
- `Field(gt=0, max_length=50, description="...")` for constraints; `@field_validator("x")` and `@model_validator(mode="after")` for custom rules.
- `model_config = ConfigDict(frozen=True, extra="forbid")`.
- `BaseSettings` reads env vars/`.env` into a typed object — use it for config.
- Compared to dataclasses: dataclass = static shape, no runtime check, cheap. Pydantic = runtime validation + serialization + JSON schema; use at boundaries (HTTP, files, env).

### FastAPI
- `app = FastAPI()`; `@app.get("/items/{item_id}")` on a function whose parameters become: path params (in the route), query params (simple types not in the route), body (Pydantic model). Return value is serialised; `response_model=` or return annotation constrains/documents it.
- `async def` handlers run on the loop; `def` handlers run in a threadpool automatically. Use `def` if you call blocking code.
- `HTTPException(status_code=404, detail="...")` for error responses. Custom exception handlers via `@app.exception_handler(MyError)`.
- Dependencies: `def get_db() -> Iterator[Session]: ...; yield session` then `db: Session = Depends(get_db)`. Same fixture mental model as pytest; supports `yield` for cleanup, sub-dependencies, and overrides in tests (`app.dependency_overrides`).
- `APIRouter` splits routes across modules; `app.include_router(r, prefix="/v1", tags=["items"])`.
- Lifespan: `@asynccontextmanager async def lifespan(app): ...startup; yield; ...shutdown` — connect pools here.
- `/docs` (Swagger) and `/openapi.json` are generated from your types. Free.
- Testing: `TestClient(app)` (sync, wraps httpx) — no server needed.

## Copy
The `app/` package here is the reference. Type it out module by module, then run:
```bash
uv add fastapi uvicorn pydantic-settings && uv add --dev pytest httpx
uv run uvicorn app.main:app --reload
uv run pytest
```
Open http://127.0.0.1:8000/docs.

## Analytical reading
`codebase-reading/README.md`, Day 10 (`fastapi/routing.py`; `pydantic` `BaseModel` surface).

## Build task (90 min)
Extend the reference: add a `PATCH /notes/{id}` with a partial-update model (all fields optional; use `model_dump(exclude_unset=True)`), pagination on `GET /notes` (`limit`/`offset` with `Field(le=100)`), a `Settings` class with `APP_NAME` and `MAX_NOTES` from env, and an exception handler for `NoteNotFound`. Tests for each. Then swap the in-memory repo for SQLite on Day 11.
