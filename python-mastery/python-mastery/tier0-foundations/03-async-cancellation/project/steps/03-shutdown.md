# Step 3 — Signals

**Checkpoint:** `uv run pytest ../checkpoints`

## What has to be true

`main(urls, grace=...)` installs handlers, runs the fetcher, and returns a process-style code.

- SIGINT: stop dispatching, wait up to `grace` seconds for in-flight work, then cancel. Return 130. The log line contains `grace period`. On Windows there is no `loop.add_signal_handler`; `signal.signal` plus `signal.raise_signal` is the path the test uses.
- SIGTERM (POSIX only): a subprocess running `python fetchd.py <url>` exits 143. The test locates the file via `Path(fetchd.__file__)`, so the module you run is the one pytest imported.

## Finish

All checkpoint tests pass. Write the shutdown order in `NOTES.md` before you open `reference/fetchd.py`.

## Explain it back

1. Why can't Windows deliver SIGTERM to this process, and what does the test do instead?
2. What would a grace period of 0 do to a request that has already connected?
