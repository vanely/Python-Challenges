# Day 8: Async, the GIL, threads vs processes

## Objectives
- Write `asyncio` code fluently (this is your strongest transfer from TS)
- Know exactly what the GIL does and doesn't do
- Pick correctly between asyncio, threads, and processes for a given workload

## Readings

| Source | Where | Read |
|---|---|---|
| asyncio | https://docs.python.org/3/library/asyncio-task.html | Coroutines, `create_task`, `gather`, `TaskGroup`, `wait_for`, `Semaphore` |
| Event loop | https://docs.python.org/3/library/asyncio-eventloop.html#running-blocking-code-in-threads | `run_in_executor` / `asyncio.to_thread` |
| httpx async | https://www.python-httpx.org/async/ | All |
| `concurrent.futures` | https://docs.python.org/3/library/concurrent.futures.html | `ThreadPoolExecutor`, `ProcessPoolExecutor`, `as_completed` |
| GIL | https://realpython.com/python-gil/ "What Is the Python Global Interpreter Lock (GIL)?" | All |
| Free-threading (3.13+) | https://docs.python.org/3/howto/free-threading-python.html | Skim — know it's coming, not yet default |
| *Fluent Python* ch. 19 "Concurrency Models in Python" | Book | All — best conceptual treatment |
| *Fluent Python* ch. 21 "Asynchronous Programming" | Book | Through "Asynchronous Context Managers" |
| Real Python | "Async IO in Python: A Complete Walkthrough" | All |

## Reading summaries

### asyncio ≈ the JS event loop, but explicit
| JS | Python |
|---|---|
| `async function f()` | `async def f()` |
| `await p` | `await coro` |
| `Promise.all([a(), b()])` | `await asyncio.gather(a(), b())` |
| `Promise.allSettled` | `gather(..., return_exceptions=True)` |
| `Promise.race` | `asyncio.wait(..., return_when=FIRST_COMPLETED)` |
| `setTimeout` | `await asyncio.sleep(s)` |
| Fire-and-forget | `asyncio.create_task(coro)` — **keep a reference** or it can be GC'd |
| Timeout | `async with asyncio.timeout(5):` or `wait_for` |
| top-level await | `asyncio.run(main())` — there is no implicit loop |
| `for await` | `async for` |
| `await using` | `async with` |

Differences that bite:
- **Calling a coroutine doesn't run it.** `f()` returns a coroutine object. You must `await` it or wrap it in a task. Unawaited coroutines trigger a `RuntimeWarning`.
- Nothing is async unless you're in an async function *and* using async libraries. `time.sleep`, `requests`, `open()` block the whole loop. Use `asyncio.sleep`, `httpx.AsyncClient`, `aiofiles` (or `to_thread`).
- `asyncio.TaskGroup` (3.11+) is structured concurrency: all tasks finish or all cancel. Prefer it to bare `gather` for new code.
- `asyncio.Semaphore(n)` for bounded concurrency — the standard way to say "at most 10 in flight."
- Async generators (`async def` with `yield`) and async context managers exist and are common in libraries.

### The GIL
- One thread executes Python bytecode at a time per process. Threads still interleave, and **I/O releases the GIL** — so threads are fine for I/O-bound work and useless for CPU-bound pure-Python work.
- C extensions (numpy, polars, hashlib, zlib) release the GIL during heavy computation, so multi-threading *does* help there.
- 3.13 ships an optional free-threaded build (`python3.13t`); not the default, most libs not yet certified. Don't design around it yet.

### Choosing a model
| Workload | Use | Why |
|---|---|---|
| Many network/disk waits, you control the code | `asyncio` | Cheapest concurrency; single thread; explicit scheduling |
| Blocking I/O in libraries you don't control | `ThreadPoolExecutor` / `asyncio.to_thread` | GIL is released during I/O |
| CPU-bound pure Python | `ProcessPoolExecutor` / `multiprocessing` | Sidesteps the GIL with separate interpreters; args must be picklable |
| CPU-bound numeric | numpy/polars in threads | Extension releases the GIL |

## Copy
`copy/01_asyncio_basics.py` → `copy/02_async_http.py` (needs network) → `copy/03_threads_vs_processes.py`

## Analytical reading
`codebase-reading/README.md`, Day 8 (`httpx/_client.py` — how sync and async clients share code).

## Build task (90 min)
An async link checker: given a file of URLs, fetch each `HEAD` with `httpx.AsyncClient`, bounded to 10 concurrent via `Semaphore`, 5 s timeout each, retry once on `httpx.TransportError`, and print a table of URL / status / ms. Use `TaskGroup`. Then re-implement with `ThreadPoolExecutor` + sync `httpx.Client` and compare wall time on ~50 URLs. Write down which was faster and why.
