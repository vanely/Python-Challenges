# Tier 1 — Data-model fluency (5–6 weeks)

Fluent Python, read properly, plus reimplementing the stdlib pieces you use most. The goal is that no dunder, protocol, or "magic" in a library surprises you again — you can predict what Python will do and why.

## Weekly plan

| Week | Fluent Python (2nd ed.) | Copy | Source to read | Build |
|---|---|---|---|---|
| 1 | Ch. 1 Data Model; Ch. 2 Sequences; Ch. 3 Dicts & Sets | `copy/01_sequence_protocol.py` | `Lib/collections/__init__.py` (`OrderedDict`, `ChainMap`, `UserDict`), `Objects/dictobject.c` header comment | `project/lru.py`: reimplement `functools.lru_cache` (typed, thread-safe, `cache_info`, `cache_clear`) |
| 2 | Ch. 5 Data Class Builders; Ch. 6 Object References, Mutability, Recycling; Ch. 7 Functions as First-Class Objects | `copy/02_dataclass_lite.py` | `Lib/dataclasses.py` in full; `Lib/copy.py`; `Lib/weakref.py` | `project/dataclass_lite.py`: `@record` decorator generating `__init__/__repr__/__eq__/__hash__`, `frozen`, `slots`, `field(default_factory)` via `exec` like the real one |
| 3 | Ch. 9 Decorators & Closures (skim, you did 0.2); Ch. 10 Design Patterns w/ First-Class Functions; Ch. 12 Special Methods for Sequences; Ch. 13 Interfaces, Protocols, ABCs | `copy/03_operators_abcs.py` | `Lib/_collections_abc.py` (how `Sequence` gives you `__contains__`/`__iter__`/`index` from `__getitem__`+`__len__`); `Lib/numbers.py` | `project/vector.py`: n-dimensional `Vector` with full operator overloading, `__hash__`, `__format__`, `__bytes__`/`frombytes`, `__getattr__` for `.x/.y/.z/.t`, pickling — then register it with `numbers.Real`-style ABCs |
| 4 | Ch. 14 Inheritance: for better or worse; Ch. 16 Operator Overloading; Ch. 17 Iterators, Generators, Classic Coroutines | `copy/04_iteration_protocols.py` | `Lib/itertools` docs' pure-Python equivalents; `Objects/typeobject.c` `mro_implementation` comment (C3) | **tinyorm v2**: `ForeignKey` with lazy related-object descriptor and reverse manager (`author.posts`), `select_related` JOIN, `Q` objects with `& | ~`, `__iter__`-driven `QuerySet` that yields lazily instead of caching a list, `bulk_create` |
| 5 | Ch. 18 with/match/else; Ch. 22 Dynamic Attributes & Properties; Ch. 23–24 (re-read now that 0.1 is done) | `copy/05_dynamic_attributes.py` | `Lib/types.py` (`SimpleNamespace`, `DynamicClassAttribute`), `Lib/enum.py` (`EnumType`, `_EnumDict`) | `project/config.py`: a `Config` object built from nested JSON with attribute access, `__getattr__` + `__dir__` + `__setattr__` guards, frozen after load, JSON-schema-ish validation, and `__init_subclass__`-registered sections |
| 6 | Consolidation | — | Re-read `Lib/dataclasses.py` and `Lib/enum.py` cold; you should now find them *obvious* | Write `NOTES.md`: for each chapter, one thing you'd previously have got wrong |

## Readings summaries — what to extract from each chapter

**Ch. 1 Data Model.** Special methods are how Python *calls your code from its own syntax*. `len(x)` → `type(x).__len__(x)` — looked up on the **type**, not the instance (so `obj.__len__ = ...` does nothing). `__repr__` vs `__str__`: repr for developers, unambiguous; str for users. `bool(x)` → `__bool__` then `__len__`. Collection API = `Iterable` + `Sized` + `Container`.

**Ch. 2 Sequences.** Container (references) vs flat (values: `array`, `bytes`, `memoryview`). Slicing → `slice` objects; `__getitem__` receives them. `+`/`*` create new; `+=`/`*=` mutate in place *if* `__iadd__` exists, else fall back to `__add__` + rebind. `list.sort` in place, `sorted` copies; both stable. `bisect` for sorted insertion; `array` + `memoryview` for zero-copy numeric work. `deque` for both-ends O(1).

**Ch. 3 Dicts & Sets.** Hashable = `__hash__` + `__eq__`, equal objects must hash equal. Dict views (`keys()/items()`) are set-like. `dict` preserves insertion order since 3.7 (compact layout: hash table of indices + dense entries array — read the `dictobject.c` comment). `__missing__` for `defaultdict`-like behaviour (only consulted by `__getitem__`, not `.get`). `ChainMap`, `Counter`, `UserDict` (subclass this, not `dict`, because `dict` methods don't call your overrides). Sets: same hashing; set ops are dunders (`__or__`, `__and__`…).

**Ch. 5 Data Class Builders.** `namedtuple` (tuple subclass, `_replace`), `NamedTuple` (typed), `dataclass` (generated methods, `field()`, `__post_init__`, `InitVar`, `ClassVar`, `frozen`, `slots`, `kw_only`, `order`, `match_args`). Dataclass is *not* a metaclass — it's a decorator that writes source and `exec`s it; that's why it's fast and composes. Pattern matching on class patterns uses `__match_args__`.

**Ch. 6 References.** Variables are labels, not boxes. `is` vs `==`. `copy.copy` is shallow; `deepcopy` walks and memoizes cycles; customise with `__copy__`/`__deepcopy__`. Default args are evaluated once (the mutable-default bug). `del` removes a reference; refcounting frees immediately; the cycle GC handles the rest. `weakref` for caches/registries that shouldn't keep objects alive (`WeakValueDictionary`, `WeakSet`, `finalize`).

**Ch. 7 First-Class Functions.** Functions have `__code__`, `__defaults__`, `__kwdefaults__`, `__annotations__`, `__closure__`. `inspect.signature` gives you `Parameter`s with kinds (POSITIONAL_ONLY, KEYWORD_ONLY, VAR_*). `partial` and `partialmethod`. `operator.itemgetter/attrgetter/methodcaller` replace trivial lambdas.

**Ch. 10 Patterns.** Strategy/Command with plain functions; `singledispatch` for visitor-like dispatch; `__call__` makes an object a callable strategy with state.

**Ch. 12 Sequence Special Methods.** Full example: a `Vector` with `__len__`, `__getitem__` (slice-aware, returning the *same type*), `__getattr__` (and why you then need `__setattr__` to block `v.x = 1`), `__hash__` via `functools.reduce(operator.xor, ...)` (or `hash(tuple)`), `__eq__` that short-circuits on length, `__format__` with custom spec.

**Ch. 13 Interfaces.** Four kinds of typing: duck (runtime, implicit), goose (runtime, explicit via ABCs + `register`/`__subclasshook__`), static duck (`Protocol`), static nominal (classes/ABCs under a checker). `collections.abc` ABCs provide mixin methods for free once you implement the abstract ones (`Sequence` gives `__contains__`, `__iter__`, `__reversed__`, `index`, `count` from `__getitem__`+`__len__`). `isinstance` against an ABC uses `__subclasshook__`.

**Ch. 14 Inheritance.** `super()` and cooperative multiple inheritance; C3 MRO (`__mro__`); mixins as the only sane use of MI; **never subclass built-ins like `dict` for behaviour changes** — subclass `UserDict`/`UserList`, because C-implemented methods bypass overrides. `__init_subclass__` for hooks. Prefer composition.

**Ch. 16 Operator Overloading.** Unary (`__neg__`, `__pos__`, `__abs__`, `__invert__`), binary with reflected (`__radd__`) and in-place (`__iadd__`) forms; **return `NotImplemented`** (not raise) for unsupported operand types so Python tries the reflected method; rich comparisons (`__lt__`… ; `functools.total_ordering`); `@` via `__matmul__`; augmented assignment on immutables just rebinds.

**Ch. 17 Iterators & Generators.** Iterable vs iterator (never make a class its own iterator if it's a collection). Generator functions; `yield from`; generator `send/throw/close`; `itertools` composition; lazy pipelines. Classic coroutines (pre-asyncio) — read for history, don't write them.

**Ch. 18 with/match/else.** `else` on `for`/`while`/`try`. `with` protocol (done in 0.1). Pattern matching: literal, capture, sequence, mapping, class patterns, guards, `|`, `as`; it's a *destructuring* tool, not a switch.

**Ch. 22 Dynamic Attributes.** `__getattr__` (fallback only) vs `__getattribute__` (everything; dangerous). `__dir__` for introspection. `__slots__` (no `__dict__`, fixed attributes, less memory; interacts badly with MI and pickling defaults). Properties as read-only computed attributes; property factories (closures generating properties — a pre-descriptor technique).

## Copy files
Five files in `copy/`, one per week, each demonstrating that week's dunders with predictable output and a `mypy --strict` pass.

## Project specs
`project/README.md` has the acceptance criteria for `lru.py`, `dataclass_lite.py`, `vector.py`, tinyorm v2, and `config.py`. Reference implementations for `lru.py` and `dataclass_lite.py` are included and tested; the others are yours alone (with the test skeletons provided).
