# mixed-executor-service — spec (you build it)

A service on your `microasgi` that correctly mixes the three execution contexts every real Python backend ends up with, and shuts down cleanly. There is no `reference/` implementation. The deadlocks and the shutdown order are the lesson, and a finished service sitting next to this file would let you skip them. Write the answers in the stage [`NOTES.md`](../../NOTES.md).

## Endpoints
| Route | Work | Where it must run |
|---|---|---|
| `POST /hash` | bcrypt-style hashing (`hashlib.scrypt(..., n=2**14, r=8, p=1)`; n=2**15 needs `maxmem=64*2**20`) of the request body | **process pool** (CPU-bound; scrypt releases the GIL, so the pool is about isolation and core budgeting — swap in a pure-Python CPU task to see the GIL argument) |
| `GET /lookup/{host}` | `socket.getaddrinfo` (blocking DNS) | **thread pool** via `asyncio.to_thread` |
| `POST /pdf` | text-extract an uploaded PDF (`pypdf`) | thread pool for I/O, process pool for the parse — chained |
| `GET /stream` | 100 SSE events, one per 50 ms | event loop |
| `GET /healthz` / `GET /readyz` | `readyz` is false until pools are warm and false again once shutdown starts | event loop |

## Requirements
1. **Pools live in lifespan.** `ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn"))` — explain in `NOTES.md` why `fork` is wrong once threads exist (and what 3.14 changed). Warm the process pool on startup (submit a no-op per worker) so the first request isn't slow.
2. **Request-scoped context everywhere.** A `request_id` `ContextVar` set by middleware must appear in log lines emitted from the thread pool *and* from the process pool. Threads: `to_thread` copies context; `run_in_executor` doesn't — prove it with a test. Processes: context doesn't cross pickling — pass it explicitly and re-set it in the worker via an `initializer`/wrapper. Wire a `logging.Filter` that reads the var.
3. **Bounded concurrency.** A `Semaphore` in front of the process pool sized to `cpu_count()`; excess `POST /hash` requests wait, and `GET /stream` still streams while they wait (prove the loop isn't blocked — a test that opens `/stream` while 2×cpu hash requests are in flight and asserts first-byte latency < 100 ms).
4. **Cancellation.** If the client disconnects mid-`/hash`, the awaiting coroutine is cancelled — but the scrypt keeps running in the worker (you can't cancel a process pool future once it's running). Document this honestly; then implement the mitigation: a per-request "still wanted" check before submitting, and a hard cap on queued work (`asyncio.Queue(maxsize)`) that returns 503 when full.
5. **Graceful shutdown**, in this order, with a test that asserts the order: readiness → false; stop accepting (uvicorn does this on SIGTERM); wait up to N s for in-flight requests; `thread_pool.shutdown(wait=True, cancel_futures=True)`; `process_pool.shutdown(wait=True, cancel_futures=True)`; exit 0. Under `uvicorn --timeout-graceful-shutdown 10`. Send SIGTERM in a subprocess test and assert exit code and that a started stream completed.
6. **Structured logging**: JSON lines with `ts, level, request_id, pid, thread, msg`.

## Tests to write
- `to_thread` vs `run_in_executor` contextvar propagation
- `/hash` runs in a different PID; `/lookup` runs in a different thread but same PID
- concurrency bound: N+1 concurrent hashes → the N+1th starts only after one finishes
- event loop stays responsive under CPU load (first-byte latency)
- 503 when the queue is full
- SIGTERM ordering via subprocess (copy the pattern from Tier 0.3's `test_fetchd.py`)

## Readings before starting
`concurrent.futures` source (`thread.py`, `process.py` — read `_ExecutorManagerThread`), `asyncio.to_thread` source (10 lines — see the `contextvars.copy_context()`), PEP 567, `multiprocessing` "Contexts and start methods", uvicorn `server.py` `shutdown()`.
