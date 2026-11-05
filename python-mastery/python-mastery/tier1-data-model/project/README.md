# Tier 1 projects — acceptance criteria

## 1. `lru.py` — reimplement `functools.lru_cache` (week 1)
- `@lru(maxsize=128, typed=False)` and bare `@lru`; `maxsize=None` = unbounded
- O(1) get/put using a doubly-linked list + dict (the real one uses a circular list with a sentinel — do the same; read `Lib/functools.py` `_lru_cache_wrapper` **after** you've tried)
- Key from `(*args, *sorted kwargs items)` with `typed` distinguishing `1` from `1.0`; unhashable args raise `TypeError`
- Thread-safe (`RLock`); exceptions don't poison the cache
- `.cache_info() -> CacheInfo(hits, misses, maxsize, currsize)`, `.cache_clear()`, `.cache_parameters()`, `__wrapped__`
- Typed: `Callable[P, R] -> _LruWrapper[P, R]` (a Protocol or generic class exposing the extras)
- Tests: eviction order, `typed`, kwargs order independence, thread hammering (no lost updates), recursion (`fib(300)`)
Reference: `lru.py` + `test_lru.py`.

## 2. `dataclass_lite.py` — `@record` (week 2)
- Reads annotations from the class (`__annotations__`, respecting `ClassVar`), generates `__init__`, `__repr__`, `__eq__`, and `__hash__` (when `frozen=True`) **by building source text and `exec`-ing it**, exactly like `dataclasses`
- `field(default=..., default_factory=..., repr=True, compare=True)`; mutable default detection (`list/dict/set` → `ValueError`)
- `frozen=True` via `__setattr__`/`__delattr__` raising `FrozenInstanceError`; `slots=True` by creating a *new* class with `__slots__` (you can't add slots after the fact — see how `dataclasses._add_slots` does it)
- Inheritance: parent fields first, child overrides by name
- `__match_args__`, `fields(cls)`, `asdict(obj)`, `replace(obj, **changes)`
- Tests mirror `test_dataclasses.py` subsets
Reference: `dataclass_lite.py` + `test_dataclass_lite.py`.

## 3. `vector.py` — n-D Vector (week 3)
Fluent Python ch. 12 + 16 in full, plus: `__bytes__`/`frombytes` with `array` + `memoryview`; `__format__` supporting `'h'` (hyperspherical) spec; `__matmul__`; `__hash__` via `reduce(xor)`; `__getattr__` for `x,y,z,t` **and** `__setattr__` rejecting single-letter lowercase names; slicing returns `Vector`; `__eq__` short-circuits on `len`; `__abs__`, `__neg__`, `__pos__`; `__add__/__radd__/__mul__/__rmul__` with `NotImplemented` on foreign types; pickle round-trip; `Vector` registered as `numbers.Real`? (decide, justify in NOTES). Test skeleton: `test_vector.py`.

## 4. tinyorm v2 (week 4)
Extend Tier 0.1's `tinyorm`:
- `ForeignKey(Model)` field: stores `<name>_id`; `post.author` is a **lazy** descriptor that queries on first access and caches on the instance; `post.author = author_obj` sets the id; reverse accessor `author.posts` returns a QuerySet-backed manager (`RelatedManager`) — implemented with `__set_name__` + `contribute_to_class`-style hook
- `select_related("author")`: one JOIN; hydrate both objects from the row
- `Q(price__gt=5) | Q(name="x")`, `~Q(...)`: operator overloading building an expression tree; `filter(Q(...) & Q(...))`
- `QuerySet.__iter__` yields lazily from the cursor (no list cache) *and* `list(qs)` still works twice (decide: re-query or cache? Django caches. Implement a `.iterator()` that doesn't)
- `bulk_create(objs)` with one `executemany`
- `Model.__init_subclass__` variant in a branch → `NOTES.md` on which you'd keep
Test skeleton: `test_tinyorm_v2.py` (write against your own package).

## 5. `config.py` (week 5)
- Load nested JSON/TOML into a `Config` with attribute access (`cfg.db.pool.size`), `__getattr__` + `__dir__` + `__repr__`, frozen after load (`__setattr__` guard), `__slots__` on the node class
- Sections are classes registered via `__init_subclass__(name=...)` with typed fields (reuse `@record`) and validated on load: missing/extra keys, type mismatches, `Literal` choices, ranges — errors collected and reported together with dotted paths
- `Config.from_env(prefix="APP_")` overlaying env vars with type coercion
- `__getattr__` must not swallow real `AttributeError`s from inside properties (classic bug — test it)
Test skeleton: `test_config.py`.
