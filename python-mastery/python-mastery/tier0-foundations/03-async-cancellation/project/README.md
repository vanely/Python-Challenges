# Project: `fetchd` — rate-limited fetcher with graceful shutdown

## Spec
A library + CLI that fetches a list of URLs concurrently with:
- **Bounded concurrency** (`Semaphore(n)`) *and* a **token-bucket rate limit** (`rate` req/s, burst `b`) — these are different constraints; implement both
- **Per-request timeout** via `asyncio.timeout`, and a **global deadline** for the whole run
- **Retry with backoff + jitter** on `httpx.TransportError` and 5xx; never on 4xx; respect `Retry-After` if present
- **Structured concurrency**: one `TaskGroup`; a single failure of a *non-retryable programming error* cancels everything; per-URL fetch failures are recorded as results, not raised
- **Graceful shutdown** on SIGINT/SIGTERM: stop dispatching (and retrying), let in-flight requests finish within a grace period (`main(urls, grace=2.0)`), then cancel; exit code 130/143. On Windows the loop has no `add_signal_handler`: fall back to `signal.signal`; only Ctrl-C (130) is deliverable there
- **Results are streamed** to the caller as they complete (an async generator), not collected at the end
- **Injectable transport** so tests never hit the network (`httpx.MockTransport`)
- **Testing without real time**: the token bucket takes a `clock: Callable[[], float]` and `sleep: Callable[[float], Awaitable[None]]` so tests can drive it deterministically

## API
```python
async with Fetcher(concurrency=10, rate=5.0, burst=5, timeout=5.0, retries=3, transport=None) as f:
    async for result in f.fetch_all(urls, deadline=60):
        ...   # FetchResult(url, status, elapsed, attempts, error)
```

## Tests to write
Token bucket: timing with a fake clock. Rate + concurrency limits actually enforced (count peak in-flight; assert timestamps). Retry: 503 then 200 → 2 attempts; 404 → 1 attempt, recorded as error. Timeout per request recorded, run continues. Global deadline cancels remaining with correct results. Cancellation mid-run: cancel the consumer task, assert in-flight requests were cancelled and the `Fetcher` exited cleanly (no "Task was destroyed but it is pending" warnings — assert via `pytest.warns`/`recwarn`). Signal handling: run `main()` in a subprocess against a local socket that accepts but never replies, send SIGTERM once it has connected (not after a `sleep`), assert exit 143; in-process, `signal.raise_signal(SIGINT)` mid-request → 130 after the grace period.

## Reference
`fetchd.py` + `test_fetchd.py`. Run `pytest -q` (needs `pytest-asyncio`, `httpx`).
