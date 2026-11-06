# microasgi — build Starlette to understand Starlette

~450 lines of framework, 12 tests, runs under uvicorn. This is a **reference implementation**: build your own from the spec first, then diff against this one.

```
pip install -e ".[dev]"
pytest
uvicorn example:app --reload
curl localhost:8000/items/1
curl -N localhost:8000/events          # SSE
```

## Spec (build this before reading `src/`)

1. **Types.** `Scope`, `Receive`, `Send`, `ASGIApp` aliases. Nothing else — the ASGI interface is the whole abstraction.
2. **Request** over `scope`+`receive`: `method`, `path`, `headers` (case-insensitive `Mapping`), `query_params`, `path_params`, `state`, `stream()`, `body()` (cached — `receive` is a queue, a second read would hang), `json()`. Raise `ClientDisconnect` on `http.disconnect`.
3. **Responses are ASGI apps**: `await response(scope, receive, send)`. `Response`, `PlainTextResponse`, `HTMLResponse`, `JSONResponse`, `StreamingResponse` (no content-length; each chunk a `more_body: True` send). Optional `background` runs after the final body send.
4. **Routing.** `compile_path("/items/{id:int}")` → regex + convertor map. `Route` (methods; GET implies HEAD; handler receives `request` only if its signature asks for it, plus path params by name). `WebSocketRoute`. `Mount(prefix, app)` appending the prefix to `root_path` and leaving `path` (the full request target, per the ASGI spec) alone; every route matches on `path` minus `root_path` (Starlette's `get_route_path`), so `uvicorn --root-path` works too. `Router` is an ASGI app: 404 on no match, 405 on method mismatch, and it must not answer lifespan.
5. **Middleware, pure ASGI only** (`__init__(app, **opts)`, `async __call__(scope, receive, send)`): `RequestIdMiddleware` (contextvar + response header), `TimingMiddleware` (`Server-Timing` header + log line), `ExceptionMiddleware` (exception type → handler via MRO lookup; must not try to respond if `http.response.start` already went out), `ServerErrorMiddleware` (outermost; 500 then re-raise so the server logs). Then a `DispatchMiddleware` adapter giving the `dispatch(request, call_next)` shape — **without spawning a task**, so contextvars flow both ways. State in one sentence what it costs (buffering) and when that's unacceptable.
6. **App.** Route decorators, `add_middleware`, lazily built stack `ServerError → user… → Exception → Router`, `state` dict, lifespan as an `asynccontextmanager` taking the app; correct `lifespan.startup.failed` / `shutdown.failed` events.
7. **WebSocket**: `accept`, `receive_text`, `send_text`, `close`, `WebSocketDisconnect`.
8. **Testing**: `httpx.ASGITransport` client; a manual lifespan driver (httpx doesn't run lifespan); a queue-based websocket tester.

### Acceptance tests (all in `tests/`)
routing + convertors + 404/405/HEAD · cached body + query + headers · HTTPException and custom handler · unhandled error → 500 + re-raise · contextvars visible in handler through pure-ASGI middleware and reset afterwards · dispatch adapter sees handler-set contextvars · streaming has no content-length and background runs after · lifespan sets shared state and shutdown runs · startup failure surfaces · Mount extends root_path and keeps path · server root_path is stripped before routing · websocket echo.

## Exercises after it works
- Add `Query`/`Body` parameter injection with pydantic validation → you've written FastAPI's core.
- Add a `StaticFiles` mount with `aiofiles`, `Range` support and `ETag`.
- Replace `DispatchMiddleware` with Starlette's task-plus-memory-channel version, write the test that shows contextvars from the handler *don't* reach the middleware, then explain why they chose it anyway (streaming `call_next`).
- Implement `http.disconnect` detection during a long streaming response and cancel the generator.
- Load test with `oha -z 10s http://localhost:8000/items/1` under `uvicorn --workers 4`; then profile a worker with `py-spy top --pid`. Where does time go? (Hint: mostly h11 and the event loop, not your framework — that's the point.)

## NOTES.md prompts
Line count vs Starlette (`cloc`); which Starlette features you skipped and what each would cost; the one design decision you'd argue with Starlette about.
