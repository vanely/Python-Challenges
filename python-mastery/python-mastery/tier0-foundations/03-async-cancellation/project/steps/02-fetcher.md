# Step 2 — Fetch, retry, bound

**Checkpoint:** `uv run pytest ../checkpoints/test_fetchd.py -k "token_bucket or retry or transport_error or concurrency or timeout or deadline or cancellation or stop_prevents"`

## What has to be true

The API in `README.md`. Tests never touch the network: they pass `httpx.MockTransport`.

- One `TaskGroup`. A per-URL HTTP failure is a `FetchResult` with `error` set, not an exception that cancels the group.
- Retry `httpx.TransportError` and status ≥ 500, with backoff. Do not retry 4xx. A 503 then 200 is two attempts. A 404 is one attempt.
- `Semaphore(concurrency)` caps in-flight requests. The rate limit is separate; both apply.
- A per-request timeout is recorded on that result and the run continues.
- `deadline` on `fetch_all` stops new work. Already-recorded results stay.
- Cancelling the consumer cancels in-flight requests and leaves no "Task was destroyed" warning.
- `stop` (or the equivalent the tests call — read the test, the name is part of the spec) stops dispatching further URLs.

`FetchResult` is a dataclass: `url, status, elapsed, attempts, error`.

## Explain it back

1. Which failures are results, and which failures are allowed to cancel the `TaskGroup`?
2. Why isn't the semaphore a substitute for the token bucket?
