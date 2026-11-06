# 0.3 — Async done right: cancellation, structured concurrency, shutdown

DRF is sync. This module makes asyncio's *hard* parts — cancellation, timeouts, shutdown, and the exact behaviour on Ctrl-C — concrete and testable.

## Objectives
- State precisely what happens when a task is cancelled: where `CancelledError` is raised, what `finally` sees, what `shield` does, why swallowing it is a bug
- Use `TaskGroup` and `asyncio.timeout` as the default structure; know when `gather` is still right
- Implement graceful shutdown: signal handling, draining, deadline, and exit codes
- Test async code with `pytest-asyncio` deterministically (no `sleep`-based flakiness)

## Readings

| Source | Where | Read |
|---|---|---|
| asyncio: Coroutines and Tasks | https://docs.python.org/3/library/asyncio-task.html | **All**, especially "Task Cancellation", "Timeouts", "Task Groups", "Shielding", `Task.cancel` semantics, `uncancel` |
| asyncio: Developing with asyncio | https://docs.python.org/3/library/asyncio-dev.html | Debug mode, "Detect never-awaited coroutines", logging |
| asyncio: Event loop — signals | https://docs.python.org/3/library/asyncio-eventloop.html#unix-signals | `add_signal_handler` |
| asyncio: Synchronization primitives | https://docs.python.org/3/library/asyncio-sync.html | `Lock`, `Event`, `Semaphore`, `Barrier` |
| `contextvars` | https://docs.python.org/3/library/contextvars.html | All; note tasks copy the context at creation |
| Nathaniel J. Smith, "Notes on structured concurrency, or: Go statement considered harmful" | https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/ | All. The essay behind `TaskGroup`. |
| Nathaniel J. Smith, "Timeouts and cancellation for humans" | https://vorpus.org/blog/timeouts-and-cancellation-for-humans/ | All. Explains why cancel scopes beat per-call timeouts. |
| Trio docs: Cancellation and timeouts | https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts | For contrast with asyncio's edge-triggered cancellation |
| Fluent Python ch. 21 | Book | Re-read "Delegating Tasks to Executors" and "Asynchronous Context Managers" |
| CPython source | `Lib/asyncio/tasks.py` → `Task.cancel`, `Task.__step`, `_cancel_requested`, `uncancel`; `Lib/asyncio/taskgroups.py`; `Lib/asyncio/timeouts.py` | Read `TaskGroup.__aexit__` to see how one failure cancels siblings and why `uncancel` exists |
| `pytest-asyncio` | https://pytest-asyncio.readthedocs.io/ | Modes, fixtures, `asyncio_mode = auto` |

## Reading summaries

### Cancellation semantics (the part everyone gets wrong)
- `task.cancel()` **requests** cancellation: the `CancelledError` is raised at the **`await` where the task is currently suspended** (it can only be cancelled while suspended). If the task hasn't started yet, its body — including `try/finally` — never runs. Code between awaits is never interrupted.
- `CancelledError` is a `BaseException` (since 3.8). `except Exception:` does **not** catch it — good. Catching it and not re-raising is almost always a bug: the canceller (e.g. a `TaskGroup`, a `timeout`) is waiting for that task to *finish cancelling*.
- `finally:` blocks run. If you `await` inside `finally` during cancellation, you can be cancelled *again*. Use `asyncio.shield()` for a critical cleanup await, or better, keep cleanup sync.
- `asyncio.shield(coro)` protects the inner from *outer* cancellation but the outer still gets `CancelledError`; the inner keeps running detached. Use rarely (commit a DB write already in flight).
- 3.11+: `Task.cancelling()` counts pending requests; `uncancel()` decrements. `asyncio.timeout()` uses these so a timeout that fires inside an outer cancellation doesn't swallow the outer cancel. If you catch `CancelledError` to convert it, you must respect that counter — this is why you shouldn't do it by hand.
- Cancelling a task that's already done is a no-op; cancelling one that's blocked in a thread (`to_thread`) cancels the *await*, not the thread. The thread keeps running to completion.

### Structured concurrency
- `async with TaskGroup() as tg: tg.create_task(...)` — the block doesn't exit until all tasks finish. First exception cancels the rest, waits for them, then raises an `ExceptionGroup`. Use `except*`.
- `gather(*coros)` returns results in order; with `return_exceptions=False` (default), the first exception propagates **but the other tasks keep running** — that's the footgun. `gather` is still fine for a fixed set of independent awaitables where you want ordered results and no sibling cancellation.
- `asyncio.timeout(s)` / `timeout_at()` are cancel scopes: cancel the current task at the deadline and convert to `TimeoutError` on exit. Since 3.12 `wait_for` is implemented on top of `timeout()`; prefer `timeout()` because it scopes a whole block rather than one awaitable.
- Fire-and-forget: `create_task` **and keep a reference** (`self._tasks.add(t); t.add_done_callback(self._tasks.discard)`), or the task can be garbage-collected mid-flight.

### Graceful shutdown pattern
1. `loop.add_signal_handler(SIGTERM, stop_event.set)` (and SIGINT). Don't raise from signal handlers. POSIX only: Windows loops raise `NotImplementedError`, so fall back to `signal.signal(s, lambda n, _f: loop.call_soon_threadsafe(...))` — and there only SIGINT (Ctrl-C) is ever delivered.
2. Main body runs inside a `TaskGroup`; a watcher task awaits `stop_event.wait()` then cancels the group's work (or sets a flag producers check).
3. Drain: stop accepting new work; let in-flight finish under `asyncio.timeout(grace)`; then hard-cancel what's left.
4. Cleanup in `finally` (sync where possible). Exit code: 0 on clean, 130 on SIGINT, 143 on SIGTERM, 1 on error.
5. `asyncio.run()` already cancels remaining tasks and shuts down async generators/executors on exit — but relying on it skips your drain.

### Testing async
- `asyncio_mode = "auto"` in `pyproject.toml`; `async def test_*` just works.
- Never test timing with real `sleep`. Use `asyncio.Event`s to sequence, or `unittest.mock.patch("asyncio.sleep")`, or drive with a controllable clock.
- Test cancellation by creating a task, letting it reach an await (`await asyncio.sleep(0)` yields once), cancelling, and awaiting it with `pytest.raises(asyncio.CancelledError)`.

## Copy
`copy/01_cancellation.py` — every semantic above, demonstrated with prints you can predict first.
`copy/02_structured.py` — `TaskGroup` vs `gather` failure behaviour, `timeout`, bounded concurrency, keeping task refs, `contextvars` propagation.
`copy/03_shutdown.py` — a runnable service with signal handling and drain; send it SIGINT/SIGTERM (Windows: Ctrl-C only) and read the log.

## Analysis prompts
1. In `Lib/asyncio/tasks.py`, trace `Task.cancel()` → `__step` → `coro.throw(CancelledError)`. At what point is `_must_cancel` cleared? What does `_fut_waiter` have to do with it?
2. In `taskgroups.py`, why does `__aexit__` call `self._parent_task.uncancel()` and under what condition does it re-raise `CancelledError` instead of the `ExceptionGroup`?
3. Trio uses *level-triggered* cancel scopes; asyncio uses *edge-triggered* `cancel()`. Explain the difference with a concrete case where a cancelled asyncio task can get "un-cancelled" by catching and continuing, and why Trio makes that impossible.
4. `asyncio.to_thread` can't cancel the thread. Design (in prose) how you'd make a blocking call cancellable: cooperative flag, `concurrent.futures` + `shutdown(cancel_futures=True)`, or subprocess. When is each right?

## Build: rate-limited fetcher with graceful shutdown
Spec in `project/README.md`. Reference implementation there, with tests that exercise cancellation deterministically.
