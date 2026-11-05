# perflab — Tier 2 extension of the Tier 0.4 lab

Start from `tier0-foundations/04-profiling/lab/` (copy it here). Add:

## v3b — Cython that actually wins
The Tier 0 Cython version didn't beat v1 because its loop was Python-object traffic. Make Cython earn its keep:
1. Move p95 to a **typed-memoryview quickselect** (`long[::1]`), `nogil`, and compare against `list.sort()` + index on the same latency lists. Expect a large win at ≥100k elements.
2. Parse latency with a hand-rolled `cdef int parse_int(const char*, Py_ssize_t)` over `bytes` lines (`open(path, "rb")`) instead of `str.split` + `int()`. Now the parse phase is native.
3. Inspect `v3_parse.html`: the inner loop must be white.

## v4 — Rust/PyO3
`../rust-ext/` is a complete scaffold: parse the whole file in Rust, aggregate into `HashMap<(u16, String), Vec<u32>>`, compute mean/p95/unique users, return a Python dict. Build with `maturin develop --release`, then add `v4_rust.py` to `bench.py`. Expect it to beat everything except possibly polars — then make it beat polars by adding `rayon` parallel parsing (`par_lines`) and releasing the GIL (`py.allow_threads`).

## v5 — free-threaded
Split the file into N byte ranges; parse each in a thread using **v1's pure-Python parser**; run under `python3.13t`. Compare to `python3.13`. Then do the same with `ProcessPoolExecutor` and explain the difference (pickling cost, startup, memory).

## Report
Extend `REPORT.md`: the full table v0–v5 on both interpreters, and a one-paragraph recommendation: for this workload, in production, which version and why (include maintenance cost, build complexity, and deployment story — wheels, cibuildwheel, platform matrix).
