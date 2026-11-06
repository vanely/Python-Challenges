# Tier 2 — The runtime (6–8 weeks)

Bytecode, the import system, memory layout, the GIL and free-threading, native extensions. After this tier, "Python is slow" becomes "this specific thing costs this much because the interpreter does X" — and you can fix it.

## Weekly plan

| Week | Reading | Copy | Build |
|---|---|---|---|
| 1–2 | CPython Internals (Shaw) ch. "Compiler", "Evaluation Loop"; tenthousandmeters #1–#4; `dis` docs; PEP 659 | `copy/01_bytecode.py` | Bytecode explorer: dump any function, annotate each op with stack effect, count specialised ops after warm-up (`dis.dis(adaptive=True)`) |
| 3 | tenthousandmeters #11 (import); `importlib` docs; PEP 451/302/420; `Lib/importlib/_bootstrap.py`, `_bootstrap_external.py` | `copy/02_import_system.py` | A meta-path finder that imports `.toml` files as modules, with lazy loading and `importlib.reload` support |
| 4 | Shaw "Memory Management"; `Objects/obmalloc.c` header; `sys.getsizeof`; PEP 683 (immortal objects); `gc` docs | `copy/03_memory.py` | Memory lab: measure per-object costs, `__slots__`, interning, `gc` generations, a reference cycle leak and its fix with `weakref` |
| 5 | Shaw "Parallelism and Concurrency"; PEP 703 (free-threaded); Sam Gross's design doc; PEP 684 (per-interpreter GIL) | `copy/04_gil_threads.py` | Free-threading experiment: run the same workload on `python3.13t` (`uv python install 3.13t`) — measure scaling, find a race, fix it |
| 6–7 | Cython docs "Language Basics", "Typed Memoryviews"; PyO3 user guide ch. 1–6; maturin docs; `cibuildwheel` docs | `copy/05_extensions.md` | **perflab**: extend Tier 0.4's lab with (a) a typed-memoryview Cython quickselect, (b) a Rust/PyO3 parser in `rust-ext/`, (c) wheels via `cibuildwheel` in CI |
| 8 | Consolidation: `Python/ceval.c` `_PyEval_EvalFrameDefault` skim; `Objects/dictobject.c`; `Objects/listobject.c` `list_resize` | — | `NOTES.md` |

## Readings

| Source | Where |
|---|---|
| CPython Internals (Anthony Shaw) | Book — the guided tour. Read with the CPython source open. |
| Python behind the scenes (Victor Skvortsov) | https://tenthousandmeters.com/tag/python-behind-the-scenes/ — #1 (VM), #2 (compiler), #3 (stepping through the source), #4 (how bytecode is executed), #5 (variables), #6 (objects), #7 (attributes), #11 (import), #12 (async), #13 (GIL) |
| `dis` module | https://docs.python.org/3/library/dis.html — the opcode table; `dis(adaptive=True)`, `show_caches` |
| PEP 659 | Specializing adaptive interpreter |
| PEP 703 | Free-threaded CPython; also https://py-free-threading.github.io/ |
| PEP 684 | Per-interpreter GIL; `concurrent.interpreters` (3.14) |
| Import system reference | https://docs.python.org/3/reference/import.html — all; then `importlib` docs |
| `gc` module + "Design of CPython's Garbage Collector" | https://devguide.python.org/internals/garbage-collector/ |
| `Objects/obmalloc.c` | Header comment: arenas → pools → blocks |
| Cython docs | https://cython.readthedocs.io — "Basic tutorial", "Language basics", "Typed memoryviews", "Pure Python mode" |
| PyO3 user guide | https://pyo3.rs — ch. 1–6 (getting started, modules, functions, classes, conversions, exceptions) |
| maturin | https://www.maturin.rs — "Tutorial" |
| cibuildwheel | https://cibuildwheel.pypa.io — "Setup" + the GitHub Actions example |
| High Performance Python (Gorelick & Ozsvald) | ch. 7 (compiling), 9 (multiprocessing), 10 (clusters — skim), 11 (less RAM) |

## Reading summaries

### How code runs
Source → tokens → AST (`ast.parse`) → symbol table → **bytecode** (`compile`, `co_code`) → the eval loop (`ceval.c`) executes ops against a value stack with a frame per call. `dis.dis(f)` shows ops; 3.11+ added **adaptive specialisation**: each `LOAD_ATTR`/`BINARY_OP`/`CALL` site starts generic, counts executions, then rewrites itself to a specialised form (`LOAD_ATTR_INSTANCE_VALUE`, `BINARY_OP_ADD_INT`) guarded by a cheap type check; polymorphic sites deoptimise. Frames became lightweight C structs (not heap `PyFrameObject`s) in 3.11 — that's most of the 3.11 speedup. 3.13 adds an experimental JIT (copy-and-patch); 3.14 makes it more real.

### Variables and scope, at bytecode level
`LOAD_FAST` (local array slot, fastest), `LOAD_DEREF` (closure cell), `LOAD_GLOBAL` (dict lookup with version-tag cache), `LOAD_NAME` (class bodies/module level). This is *why* locals are fast and why comprehensions were inlined in 3.12 (PEP 709).

### Objects and memory
Every object: `ob_refcnt`, `ob_type` (16 bytes, plus GC header for containers). `int` is variable-length; small ints (−5..256) cached; strings may be interned; 3.12 **immortal objects** (`None`, `True`, small ints…) have a saturating refcount so they're never freed and never written to (cache-friendly, needed for free-threading). Allocator: `obmalloc` serves ≤512 B from pools inside 1 MiB arenas (`pymalloc`); bigger goes to `malloc`. `sys.getsizeof` is shallow. Instance `__dict__`s share keys per class (key-sharing dicts, PEP 412) — `__slots__` removes the dict entirely. Refcounting frees acyclic garbage immediately; the **cyclic GC** runs by generation (0/1/2 with thresholds; an incremental GC shipped only in 3.14.0–3.14.4 and was reverted in 3.14.5 — 3.12, 3.13 and 3.14.5+ are generational) and only looks at container objects. `gc.disable()` during bulk loads is a legitimate optimisation; `gc.freeze()` before `fork` avoids copy-on-write blowup.

### The import system
`import a.b` → `sys.modules` check → for each `finder` in `sys.meta_path` (`BuiltinImporter`, `FrozenImporter`, `PathFinder`) call `find_spec(name, path)` → a `ModuleSpec` with a `loader` → `loader.create_module` / `exec_module` → module inserted in `sys.modules` **before** execution (that's why partial modules and circular imports behave as they do). `PathFinder` consults `sys.path_hooks` → `FileFinder` per directory, caching directory listings (`importlib.invalidate_caches()` when you create files at runtime). `__init__.py`-less directories are namespace packages (PEP 420), merged across `sys.path`. `importlib.reload` re-executes into the *same* module object (old attributes linger). `.pth` files run at startup — that's how editable installs work.

### The GIL and free-threading
One mutex; a thread must hold it to run bytecode; released every ~5 ms (`sys.setswitchinterval`) and around blocking I/O and in C code that opts out (`Py_BEGIN_ALLOW_THREADS`). Consequences: threads don't parallelise pure-Python CPU; they do parallelise I/O and GIL-releasing C (numpy, hashlib, zlib, DB drivers). **PEP 703** (3.13, `python3.13t` build): no GIL; biased reference counting (owner thread fast path) + deferred refcounting for hot objects + immortal objects; per-object locks on `dict`/`list`; single-thread cost ~40% on 3.13t (no specialisation), ~1–8% on 3.14t; C extensions must opt in (`Py_mod_gil`). Data races in your Python code that the GIL hid (`+=` on a shared counter, check-then-set) become real — the "atomic because of the GIL" folklore is over. Alternatives: `multiprocessing`/`ProcessPoolExecutor` (pickling boundary), `concurrent.interpreters` (3.14; per-interpreter GIL, share via `concurrent.interpreters.Queue` / shareable objects such as `memoryview`).

### Extensions
Two sane routes today: **Cython** (superset of Python; `cdef` types; `-a` HTML shows Python-interaction lines; typed memoryviews for arrays; great for gradually speeding existing code) and **Rust + PyO3 + maturin** (`#[pyfunction]`/`#[pyclass]`, automatic conversions, `maturin develop` for local builds, `maturin build --release` for wheels; the ecosystem's direction — polars, pydantic-core, ruff, uv, cryptography). Both release the GIL for pure-native sections (`with nogil:` / `py.detach`). Ship wheels for CPython 3.12/3.13 × linux/macos/windows via `cibuildwheel` (uses manylinux containers on Linux); always also ship an sdist. ABI3/limited API (`abi3-py312`) lets one wheel serve many Python versions at a small speed cost.

## Copy files
`copy/01_bytecode.py` — `dis` walkthroughs: loop, closure, class body, comprehension inlining, adaptive specialisation before/after warm-up, stack-effect annotation.
`copy/02_import_system.py` — walk `sys.meta_path`, write a finder+loader, namespace packages, `reload` semantics, circular import demo.
`copy/03_memory.py` — sizes, `__slots__`, interning/small-int cache, `tracemalloc` on a leak, cyclic GC generations, `gc.get_referrers`, weakref fix.
`copy/04_gil_threads.py` — GIL-bound vs GIL-releasing workloads with `ThreadPoolExecutor`/`ProcessPoolExecutor`; a race that the GIL "hides"; the same script for `python3.13t`.
`copy/05_extensions.md` — the Cython and PyO3 recipes side by side with the exact commands.

## Analysis prompts
1. `dis` a method call `obj.m(x)` in 3.10 and 3.12 (use `uv python install 3.10`). Explain every opcode difference (`LOAD_METHOD`/`CALL_METHOD` vs `LOAD_ATTR` with the method flag + `CALL`; `PRECALL` in 3.11; inline `CACHE` entries).
2. Read `_bootstrap._find_and_load_unlocked`. Why is `sys.modules[name]` set before `exec_module`? Construct a circular import that works and one that fails, and explain from this function.
3. `gc.get_stats()` before/after creating a million short-lived tuples vs a million short-lived objects with `__del__`. Explain the collection counts.
4. Run `copy/04_gil_threads.py` on 3.13 and 3.13t. Report scaling for each workload. Find which of your own libraries' C extensions declare free-threading support (`python3.13t -c "import x, sys; print(sys._is_gil_enabled())"` — a `RuntimeWarning` that the GIL was enabled means the module hasn't declared support; `-X gil=0` suppresses that check).
5. Read polars' `py-polars/src/lib.rs` top-level and `pydantic-core/src/lib.rs`. How do they structure a large PyO3 module? Where do they release the GIL?

## Build: perflab + rust-ext
`perflab/README.md` and `rust-ext/README.md`. The Rust extension scaffold is complete (Cargo.toml, pyproject with maturin, `src/lib.rs` implementing the log parser, tests, cibuildwheel workflow) but **unbuilt** here — build it locally with `maturin develop --release` and add it as `v4_rust.py` to the benchmark.
