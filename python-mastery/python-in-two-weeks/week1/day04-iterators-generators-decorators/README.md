# Day 4: Iterators, generators, context managers, decorators

These three are what make Python feel foreign to a TS developer. Give them the whole day.

## Objectives
- Explain the iterator protocol and write a generator instead of building a list
- Write and use context managers for setup/teardown
- Write decorators (with and without arguments) that preserve metadata and type-check

## Readings

| Source | Where | Read |
|---|---|---|
| Tutorial 9.8–9.10 | https://docs.python.org/3/tutorial/classes.html#iterators | Iterators, generators, generator expressions |
| `itertools` | https://docs.python.org/3/library/itertools.html | The table at the top + `chain`, `islice`, `groupby`, `batched`, `pairwise`, `takewhile` |
| `contextlib` | https://docs.python.org/3/library/contextlib.html | `contextmanager`, `suppress`, `ExitStack` |
| `functools` | https://docs.python.org/3/library/functools.html | `wraps`, `lru_cache`/`cache`, `partial`, `singledispatch` |
| PEP 343 (with statement) | https://peps.python.org/pep-0343/ | Motivation + specification |
| *Fluent Python* ch. 17 "Iterators, Generators, and Classic Coroutines" | Book | Up to (not including) classic coroutines |
| *Fluent Python* ch. 9 "Decorators and Closures" | Book | All |
| Real Python | "How to Use Generators and yield in Python"; "Primer on Python Decorators"; "Context Managers and Python's with Statement" | All three |
| Source | `contextlib.py` → `_GeneratorContextManager` | See how `@contextmanager` turns a generator into `__enter__`/`__exit__` |

## Reading summaries

### The iterator protocol
- **Iterable**: has `__iter__()` returning an iterator. Lists, dicts, strings, files, ranges.
- **Iterator**: has `__next__()` and raises `StopIteration` when done; also `__iter__` returning itself.
- `for x in xs` is sugar for `it = iter(xs); while True: try: x = next(it) except StopIteration: break`.
- Iterators are **single-pass**. `list(it)` twice gives `[...]` then `[]`. This bites TS devs who treat everything as an array.
- JS analogue: `Symbol.iterator` / `[Symbol.iterator]()` returning `{ next() }`. Same shape, but Python uses it everywhere.

### Generators
- A function with `yield` returns a generator object without running. Each `next()` runs to the next `yield`.
- `yield from sub` delegates (like `yield*`).
- Generators are lazy pipelines: read a 10 GB file line by line, filter, transform, without materializing. Chain them.
- Generator expressions `(x for x in xs)` are anonymous generators. Pass directly to `sum`, `any`, `max`, `", ".join`.
- Return type hint: `Iterator[T]` (or `Generator[YieldT, SendT, ReturnT]` if you use send/return).
- `itertools` is the generator toolbox. `islice` for pagination/limits; `chain` to concat; `groupby` requires sorted input; `batched` (3.12) for chunking.

### Context managers
- `with open(p) as f:` guarantees `f.close()` even on exception. Equivalent to `try/finally`, but reusable.
- Protocol: `__enter__` (returns the `as` value) and `__exit__(exc_type, exc, tb)` (return `True` to swallow the exception).
- `@contextlib.contextmanager` on a generator: code before `yield` is enter, after is exit. `try/finally` around the `yield` is the standard shape.
- Use for: files, locks, DB transactions, temporary cwd/env, timers, monkeypatching in tests.
- TS analogue: `using` declarations (TC39 explicit resource management) — Python has had this for 20 years.

### Decorators
- `@deco` above `def f` means `f = deco(f)`. A decorator is a function taking a function and returning a function (or anything).
- The wrapper pattern:
  ```python
  def deco(fn):
      @functools.wraps(fn)          # copies __name__, __doc__, etc. Always.
      def wrapper(*args, **kwargs):
          ...                        # before
          result = fn(*args, **kwargs)
          ...                        # after
          return result
      return wrapper
  ```
- Decorator **with arguments** is a function returning a decorator: `@retry(times=3)` → `retry(times=3)(fn)`.
- Typing: `ParamSpec` + `TypeVar` keep the wrapped signature: `Callable[P, R] -> Callable[P, R]`.
- Class-based decorators use `__call__`. Decorators can stack; bottom applies first.
- `functools.cache` memoizes; `partial` pre-binds args; `singledispatch` gives overloading by first-arg type.
- TS analogue: TS decorators are class-only and experimental; Python's are plain higher-order functions and used everywhere (`@property`, `@dataclass`, `@app.get("/")`, `@pytest.fixture`).

## Copy
`copy/01_iterators.py` → `copy/02_generators.py` → `copy/03_context_managers.py` → `copy/04_decorators.py`

## Analytical reading
`codebase-reading/README.md`, Day 4 (`contextlib.py` `_GeneratorContextManager`, `typer` decorators).

## Build task (90 min) — all three, with tests and `mypy --strict`
1. `@retry(times=3, delay=0.1, exceptions=(IOError,))` — re-raises the last exception after exhausting attempts.
2. `@timed` — logs wall time with the function name; must preserve the signature for mypy.
3. `atomic_write(path)` context manager — writes to a temp file in the same directory and renames on success; deletes the temp on failure.
4. `read_records(path) -> Iterator[dict[str, str]]` — lazily yields rows from a CSV; then `batched(read_records(p), 100)` to insert in chunks (fake the insert).
