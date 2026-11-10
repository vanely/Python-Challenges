# Step 2 — Middleware, errors, lifespan, streaming

**Checkpoint:** from `student/`, `uv run pytest ../checkpoints/test_microasgi.py -k "not mount and not root_path and not websocket"`

README items 5 and 6, plus streaming responses and background tasks.

- `RequestIdMiddleware` stores the id in `request_id_var` and puts it on the response. The contextvar is visible in the handler and reset afterwards.
- `DispatchMiddleware` runs `dispatch(request, call_next)` **without** spawning a task, so a contextvar the handler sets is still visible to the middleware. `CallNext` is the type of `call_next`.
- `HTTPException` and a custom handler. An unhandled error becomes a 500 and is re-raised.
- Lifespan is an async context manager on the app. Startup failure is reported on the lifespan protocol, not swallowed. State set during startup is visible to handlers.
- `StreamingResponse` sets no content-length. A `BackgroundTask` runs after the body is sent.

## Explain it back

1. What does spawning `call_next` in another task do to contextvars, and why does Starlette do it anyway?
