# Tier 3 — Async and systems (4–6 weeks)

Build the framework you've been using. After this tier, Starlette/FastAPI/Django-ASGI internals are readable, and you can design a service that mixes event loop, threads, and processes without deadlocks or lost cancellations.

## Weekly plan

| Week | Reading | Copy | Build |
|---|---|---|---|
| 1 | ASGI spec (all three docs); `Lib/asyncio/base_events.py` `create_server`/`_run_once`; uvicorn `protocols/http/h11_impl.py` | `copy/01_asgi_by_hand.py` | `microasgi` core: `Request`/`Response`, router with path params, `run_asgi`, works under uvicorn |
| 2 | Starlette source: `applications.py`, `routing.py`, `middleware/base.py`, `requests.py`; PEP 3333 for contrast | `copy/02_middleware_lifespan.py` | middleware stack (pure-ASGI + `BaseHTTPMiddleware`-style), lifespan events, exception handlers, background tasks, `TestClient` via `httpx.ASGITransport` |
| 3 | `contextvars` PEP 567; `asyncio` `run_in_executor`; `concurrent.futures` source; `anyio` docs "Running code in worker threads" | `copy/03_executors_contextvars.py` | `mixed-executor-service`: event loop + thread pool (blocking I/O) + process pool (CPU) + graceful shutdown + request-scoped context |
| 4 | Trio docs "Tutorial" + "Design and internals"; `anyio` design; `asyncio` streams (`StreamReader/Writer`, `Protocol`s) | `copy/04_trio_contrast.py` (needs `trio`) | streaming: a chunked/SSE endpoint and a websocket echo in `microasgi`; backpressure demo |
| 5–6 | uvicorn `config.py`, `server.py`, `supervisors/`; gunicorn arbiter (skim); `hypercorn` for HTTP/2 | — | run `microasgi` in production shape: uvicorn workers behind a reverse proxy, health/readiness, structured logging with `contextvars`, load test with `oha`/`wrk`; then `NOTES.md` comparing your framework to Starlette line-count and feature-wise |

## Readings

| Source | Where | Read |
|---|---|---|
| ASGI spec | https://asgi.readthedocs.io/en/latest/specs/main.html, `www.html`, `lifespan.html` | All three — they're short. The `scope`/`receive`/`send` triple is the whole interface. |
| Starlette source | https://github.com/encode/starlette/tree/master/starlette | `applications.py`, `routing.py` (`Route`, `Router`, `compile_path`), `middleware/base.py`, `middleware/errors.py`, `requests.py`, `responses.py` (`StreamingResponse`), `background.py`, `testclient.py` |
| uvicorn source | https://github.com/encode/uvicorn/tree/master/uvicorn | `protocols/http/h11_impl.py` (how bytes become a scope and `receive`/`send` are wired), `lifespan/on.py`, `server.py`, `config.py` |
| PEP 567 | contextvars | All |
| PEP 3156 | asyncio | Skim the "Event loop interface" and "Transports/Protocols" for the lower layer |
| Trio | https://trio.readthedocs.io/en/stable/tutorial.html and "Design and internals" | All of both |
| anyio | https://anyio.readthedocs.io | "Basics", "Tasks", "Cancellation", "Threads" — the structured-concurrency layer Starlette actually uses |
| `Lib/asyncio/base_events.py`, `selector_events.py`, `streams.py` | CPython | `_run_once`, `create_server`, `_SelectorSocketTransport`, `StreamReader.feed_data`/`readexactly` |
| Fluent Python ch. 21 | Book | Re-read fully |
| Hypercorn/HTTP2 | https://pgjones.gitlab.io/hypercorn/ | Skim |

## Reading summaries

### ASGI in one screen
An ASGI app is `async def app(scope, receive, send)`. `scope` is a dict (`type` ∈ {`http`, `websocket`, `lifespan`}, `method`, `path`, `headers` as `list[tuple[bytes, bytes]]`, `query_string`, `state`, …). `receive()` yields events (`http.request` with `body`+`more_body`, `http.disconnect`, `websocket.receive`); `send()` takes events (`http.response.start` with `status`+`headers`, `http.response.body` with `body`+`more_body`). One app instance handles every connection; per-request state lives in locals or `scope["state"]`. Lifespan: a single `lifespan` scope for the process — `lifespan.startup` → app does setup → sends `lifespan.startup.complete`; likewise shutdown. Middleware is just an app that wraps another app and intercepts `scope`/`receive`/`send`. Streaming = multiple `http.response.body` sends with `more_body: True`.

### How Starlette is put together
`Starlette` builds a middleware stack (`ServerErrorMiddleware` → user middleware → `ExceptionMiddleware` → `Router`) lazily on first call. `Router.__call__` matches `Route`s via compiled regex (`compile_path` turns `/items/{id:int}` into a regex + convertor map) and dispatches to an `endpoint` wrapped by `request_response`, which builds a `Request` (lazy body parsing via `receive`) and awaits the handler, then `await response(scope, receive, send)`. `BaseHTTPMiddleware` gives a `dispatch(request, call_next)` API by running the inner app in a task and bridging the response through a memory channel — it's *convenient but leaky* (values set in the endpoint don't propagate back up to the middleware or outer pure-ASGI middleware; the extra task and channel add overhead and complicate cancellation and disconnects); pure-ASGI middleware is what serious code uses. `BackgroundTask`s run after the response is sent. `TestClient` uses `httpx` with an ASGI transport and a portal into a running loop.

### Executors and contextvars
`loop.run_in_executor(None, fn)` → default `ThreadPoolExecutor` (size ~`min(32, cpu+4)`); `asyncio.to_thread` copies the current `contextvars.Context` into the thread — `run_in_executor` does **not**. For CPU work, `ProcessPoolExecutor` (pickling boundary; `fork` start method is unsafe with threads/async — use `spawn` or `forkserver`; 3.14 changes the default). Shutdown order matters: stop accepting → drain loop tasks → `executor.shutdown(wait=True, cancel_futures=True)`. `contextvars`: `ContextVar.set` returns a token; `reset(token)`; each task gets a *copy* at creation; `Context.run` for manual propagation; this is how request IDs get into logs without passing them around — build a `logging.Filter` that reads the var.

### Trio vs asyncio
Trio: nurseries (all tasks are children; no orphaned tasks possible), level-triggered cancel scopes (a cancelled scope stays cancelled — you can't accidentally "un-cancel"), checkpoints are explicit (`await trio.sleep(0)`), no `Future`/`Task` handles floating around. asyncio adopted the *shape* (`TaskGroup`, `timeout`) but keeps edge-triggered `cancel()`, free-floating tasks, and callback-style APIs for compatibility. `anyio` provides Trio's API on top of either loop — read it to see what "structured concurrency as a library" costs.

### Streams and backpressure
`StreamWriter.write` buffers; `await writer.drain()` waits when the transport's high-water mark is exceeded — skipping `drain` is how you get unbounded memory. Same idea in ASGI: `send` awaits the server, which applies transport backpressure; a handler that produces faster than the client reads will block on `send`, correctly. For fan-out, bounded `asyncio.Queue`s between producer and consumers.

## Copy files
`copy/01_asgi_by_hand.py` — a complete ASGI app with no framework: routing, body reading, streaming, lifespan; run with `uvicorn 01_asgi_by_hand:app`.
`copy/02_middleware_lifespan.py` — pure-ASGI middleware (timing, request-id via contextvars, error handling), a `dispatch`-style adapter, background tasks, tested with `httpx.ASGITransport`.
`copy/03_executors_contextvars.py` — `to_thread` vs `run_in_executor` context propagation, process pool with `spawn`, structured shutdown of both pools, logging filter reading a `ContextVar`.
`copy/04_trio_contrast.py` — the same fetcher/timeout/cancel demos from Tier 0.3 written in Trio; comment on each difference.

## Analysis prompts
1. In uvicorn's `h11_impl.py`, find where `receive` and `send` are defined for a request. What does `send` do when `more_body` is False? Where does backpressure enter?
2. Starlette `BaseHTTPMiddleware`: read the issue history linked in its docstring. Reproduce one of the bugs (contextvars not propagating) with a test, then fix it by rewriting the middleware as pure ASGI.
3. Trace a `TestClient` request: how does sync test code drive an async app? (`anyio.from_thread.start_blocking_portal`)
4. In `Lib/asyncio/base_events.py` `_run_once`, what are the exact steps? Where do `call_soon` callbacks run relative to I/O? What does `sys.setswitchinterval` have to do with any of this (trick question)?

## Build
- `microasgi/README.md` — spec + a reference implementation (tests included; runnable under uvicorn).
- `mixed-executor-service/README.md` — spec only; you build it (it depends on your `microasgi`).
