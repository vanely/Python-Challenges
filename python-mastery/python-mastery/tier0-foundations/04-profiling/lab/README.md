# Optimisation lab — log analytics

`gen.py` writes a synthetic access log (~500k lines by default). `v0_baseline.py` computes, per (status, endpoint):
request count, mean latency, p95 latency, unique users, and the top 10 endpoints by count — the way
someone in a hurry would write it. It is slow on purpose, in *several* distinct ways.

## Your job
1. Generate data: `python gen.py 500000 access.log`
2. Profile `v0_baseline.py` with **cProfile**, **py-spy record**, and **scalene**. Before opening any code, write down in `REPORT.md` the three biggest problems and your predicted speedup from fixing each.
3. Write `v1_algorithmic.py`: same output, pure Python, fix the algorithmic/data-structure problems only.
4. Write `v2_vectorised.py`: polars (or numpy). Aim for a single lazy query plan.
5. Write `v3_cython.pyx` (+ `setup.py` or `pyproject` with `cythonize`): the parse loop in Cython with typed variables. Compare against v1.
6. `bench.py` runs all versions on the same file, checks outputs match, and prints a table. Fill `REPORT.md` with the numbers and *why* each change mattered.

Reference implementations for v1/v2/v3 are here — do yours first. The reference numbers on the authoring machine (1 polars thread, 3.12, 200k lines):

| version | seconds | speedup |
|---|---|---|
| v0 baseline | 4.26 | 1× |
| v1 algorithmic | 0.23 | 18× |
| v2 polars | 0.11 | 39× |
| v3 cython parse + v1 aggregation | 0.28 | 15× |

Three lessons hiding in that table:
1. The **algorithmic** fix (v1) is where almost all the win is. Everything after is a smaller multiplier on a much smaller number.
2. **Cython barely beats v1, if at all.** On the authoring machine it was slower (above); on others it gave only ~1.1–1.4× over v1. The loop body is `str.split`, dict/list/set ops and `int()` — all already C, all still Python objects. Typing the locals `str`/`int` doesn't remove the object traffic. Cython pays off when the inner loop is *arithmetic on scalars or memoryviews*, not string/dict shuffling. Prove it to yourself: rewrite p95 as a typed-memoryview quickselect in Cython and compare against `list.sort()`.
3. A first `bench.py` draft timed polars at 1.6 s — because it timed `import polars`. Always import/warm up outside the timed region; the reference harness now does. Measurement bugs are the most common profiling result.

## What's wrong with v0 (don't read until you've profiled)
- Calls `re.match` with a pattern string on every line (a cache lookup plus a match object; small) and does a full `datetime.fromisoformat` + `strftime` when only the date is needed
- Collects **all** latencies per key in lists (huge memory) and sorts a copy of each per-key list for p95 → O(n log n) total, plus a full copy
- Unique users via `if user not in users_list` → O(n²)
- Top-N by sorting the whole dict every time it's called (called per key for "rank")
- String-builds the key with f-strings and then re-splits it
