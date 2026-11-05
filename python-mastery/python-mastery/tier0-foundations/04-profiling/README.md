# 0.4 — Profiling: measure before you guess

Competitive programming trains guessing at hot spots. Production trains measuring. This module is the measuring toolkit and one full optimisation lab.

## Objectives
- Choose the right tool: `timeit` (micro), `cProfile` + `snakeviz`/`pstats` (deterministic, function-level), `py-spy` (sampling, production-safe, native frames), `scalene` (CPU + memory + GPU, line-level), `tracemalloc` (allocation sources), `memray` (allocations incl. native), `line_profiler`
- Read a profile: cumulative vs total time, call counts, the "wide vs deep" shape
- Fix the bottleneck three ways and quantify each: algorithmic, vectorised (numpy/polars), native (Cython; Rust in Tier 2)
- Know CPython's cost model well enough to predict: function call overhead, attribute lookup, `for` loop vs comprehension vs builtin, string building, dict/set membership, object allocation

## Readings

| Source | Where | Read |
|---|---|---|
| `cProfile` / `pstats` | https://docs.python.org/3/library/profile.html | All; especially `sort_stats` keys and `print_callers` |
| `timeit` | https://docs.python.org/3/library/timeit.html | CLI usage, `repeat`, why min not mean |
| `tracemalloc` | https://docs.python.org/3/library/tracemalloc.html | `take_snapshot`, `compare_to`, `statistics("lineno")` |
| py-spy | https://github.com/benfred/py-spy | README: `record`, `top`, `dump`, `--native`, `--gil` |
| scalene | https://github.com/plasma-umass/scalene | README + the paper summary; understand "system time" vs "Python time" columns |
| memray | https://bloomberg.github.io/memray/ | Overview + flamegraph reporter |
| CPython perf tips (wiki) | https://wiki.python.org/moin/PythonSpeed/PerformanceTips | All — old but still right |
| "Python behind the scenes #4: how bytecode is executed" (Victor Skvortsov) | https://tenthousandmeters.com/blog/python-behind-the-scenes-4-how-python-bytecode-is-executed/ | All; sets up Tier 2 |
| Specializing adaptive interpreter (3.11+) | https://peps.python.org/pep-0659/ | Read; explains why 3.11+ is faster and what patterns benefit |
| numpy: broadcasting + vectorisation | https://numpy.org/doc/stable/user/basics.broadcasting.html | All |
| Cython tutorial | https://cython.readthedocs.io/en/latest/src/tutorial/cython_tutorial.html + "pure Python mode" | Basics; `cdef`, typed memoryviews, `-a` annotation HTML |
| High Performance Python, 2nd ed. (Gorelick & Ozsvald) | Book | Ch. 2 (profiling), 6 (matrix/vector), 7 (compiling to C), 9 (multiprocessing) |

## Reading summaries

### Which profiler
| Question | Tool |
|---|---|
| Is A faster than B? (micro) | `python -m timeit -s "setup" "stmt"`; use `min` of repeats |
| Where does time go in this script? | `python -m cProfile -o out.prof script.py` → `snakeviz out.prof` or `pstats` sorted by `cumulative` then `tottime` |
| Where does time go in a *running* process / production? | `py-spy top --pid N` / `py-spy record -o flame.svg --pid N`; `--native` to see C frames; `--gil` to see who holds it |
| Which *line* is hot, and is it Python or native? | `scalene script.py` |
| Where is memory allocated? | `tracemalloc` (pure Python allocations, in-process) or `memray run` (everything, incl. native, with flamegraphs) |
| Function-level line timing | `kernprof -l` / `line_profiler` `@profile` |

`cProfile` adds overhead and distorts (inflates call-heavy code); `py-spy` is sampling so it's cheap and safe on prod but statistical. Profile with realistic data sizes; hot spots move with N.

### CPython cost model (rules of thumb, 3.12)
- A Python function call is ~50–100 ns; a method call slightly more; attribute lookup on an instance ~20–40 ns. Inner loops that call a small function per element are dominated by call overhead → inline or vectorise.
- `for` loop appending: ~1.5–2× slower than a comprehension; both ~10–50× slower than a numpy op on the same data.
- Global name lookup > local. Bind hot globals/attributes to locals before a tight loop (`append = out.append`).
- String concatenation in a loop is O(n²) in principle; CPython has an optimisation that often hides it; `"".join()` anyway.
- `x in list` is O(n); `in set/dict` is O(1). Converting once and probing many times wins past ~10 elements.
- Allocation is expensive: creating a tuple/dict/object per element is often the real cost. `__slots__` cuts per-instance memory ~40–50% and speeds attribute access slightly.
- `sum(x for x in ...)` (generator) is slightly slower than `sum([...])` for small N due to generator overhead; but O(1) memory.
- 3.11+ specialises bytecode for stable types at each call site; polymorphic sites (same code fed ints then floats) deoptimise. Keep hot loops monomorphic.
- The GIL: threads don't help pure-Python CPU work; they do help I/O and C-extension work that releases the GIL (numpy, hashlib, zlib, most DB drivers).

### Reading `pstats`
`ncalls` (primitive/total for recursion), `tottime` (own time), `cumtime` (incl. callees). Sort by `cumtime` to find the subtree; by `tottime` to find the function to fix. `print_callers("name")` tells you *who* calls the hot function — often the fix is fewer calls, not a faster function.

### Vectorise or compile?
- **Algorithmic** first: the O(n²)→O(n log n) change beats everything else.
- **numpy/polars** when the work is "the same operation over a big array/table" — pushes the loop into C.
- **Cython** when the loop body is genuinely scalar and branchy (parsers, simulations, tree walks). Typed `cdef` variables + memoryviews; check the `-a` HTML for yellow (Python interaction) lines.
- **Rust/PyO3** (Tier 2) for the same cases when you want a real language, safety, and a sane build. Slightly more setup than Cython, much nicer to maintain.
- **Multiprocessing** when the work is embarrassingly parallel and pickling cost is small relative to compute.

## Copy
`copy/01_profilers.py` — a deliberately slow program instrumented four ways (`timeit`, `cProfile`+`pstats`, `tracemalloc`, and a `py-spy`/`scalene` command cheat sheet in comments).
`copy/02_cost_model.py` — microbenchmarks that *demonstrate* every rule of thumb above with numbers. Run it on your machine; write the numbers into the README.

## Analysis prompts
1. Profile Django's test client doing 50 requests to a trivial view (`cProfile`). Sort by `tottime`. What are the top 5 functions? How many are yours? What fraction is middleware/ORM/serialisation?
2. Read `Lib/cProfile.py` and `Lib/profile.py`. How does deterministic profiling hook in (`sys.setprofile`)? Why can it not see time in C functions called from C?
3. `py-spy --gil`: run it against a threaded pure-Python CPU script and a threaded numpy script. Explain the two outputs.
4. Read PEP 659's "Specialization" examples. Write a 10-line loop that is fast, then a change that makes the same site polymorphic and slower; measure.

## Build: the optimisation lab
`lab/README.md`. A realistic slow program (log analytics: parse, aggregate, join, rank). Profile it, then produce four versions and a written report with numbers: (1) baseline, (2) algorithmic, (3) numpy/polars, (4) Cython (Tier 2 adds Rust). Reference versions and a benchmark harness included.
