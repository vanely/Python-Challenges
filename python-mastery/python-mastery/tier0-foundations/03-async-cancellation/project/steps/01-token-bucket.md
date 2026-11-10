# Step 1 — A clock you can fake

**Checkpoint:** `uv run pytest ../checkpoints/test_fetchd.py -k token_bucket`

## What has to be true

`TokenBucket(rate, burst, clock, sleep)`. `clock()` returns seconds. `sleep` is an async function the bucket awaits. Tests pass a clock that doesn't move unless `sleep` moves it, so you cannot call `asyncio.sleep` inside the bucket.

- `burst` tokens are available immediately.
- The next acquire waits `1/rate` seconds.
- Refill stops at `burst`. Time passing does not accumulate extra tokens.

Put `fetchd.py` in a directory with the reference `pyproject.toml`'s dev dependencies (`pytest`, `pytest-asyncio`, `httpx`), `cd` there, and run the checkpoint. `reference/` is the solution.

## Explain it back

1. Why does the bucket take `clock` and `sleep` instead of calling `time.monotonic` and `asyncio.sleep` itself?
