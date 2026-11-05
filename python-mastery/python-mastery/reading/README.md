# Master reading list

Everything referenced across tiers, in one place, with what to take from each. Per-chapter summaries for Fluent Python live in `tier1-data-model/README.md`; the per-tier READMEs have the detailed extraction notes. This is the index.

## Books
| Book | Tier | How to read it |
|---|---|---|
| **Fluent Python, 2nd ed.** (Ramalho) | 1 (and 0.1, 0.3) | Cover to cover, in the Tier 1 order, with the copy file for each chapter open. The single most important book here. |
| **CPython Internals** (Shaw) | 2 | With the CPython source checked out at the tag the book targets; run every experiment. |
| **High Performance Python, 2nd ed.** (Gorelick & Ozsvald) | 0.4, 2 | Ch. 2 (profiling), 4–6 (dicts/sets, iterators, matrices), 7 (compiling), 9 (multiprocessing), 12 (field lessons). |
| **Architecture Patterns with Python** (Percival & Gregory) | 1, 4 | Ch. 1–7 for repository/UoW/service layer vs what Django gives you; good for library-API thinking. |
| **Robust Python** (Viafore) | 0.2 | Ch. 2–8 typing, 12–16 extensibility. Skim; you'll know half. |
| **Python Testing with pytest, 2nd ed.** (Okken) | 0.5, 4 | Fixtures, parametrize, plugins, `conftest` scoping. |

## PEPs (read the PEP, not a summary)
| PEP | Topic | Tier |
|---|---|---|
| 8, 20 | Style; the Zen — yes, actually read them once | — |
| 234, 255, 342, 380, 492, 525, 530 | Iterators → generators → coroutines → async: the lineage | 1, 3 |
| 3115, 487, 557, 681 | Metaclasses, `__init_subclass__`/`__set_name__`, dataclasses, `dataclass_transform` | 0.1, 1 |
| 484, 526, 544, 585, 586, 589, 591, 593, 604, 612, 613, 646, 647, 673, 675, 692, 695, 696, 698, 705, 742, 747, 764 | The typing system, in order | 0.2 |
| 3156, 492, 567 | asyncio, async/await, contextvars | 0.3, 3 |
| 3333 | WSGI (for contrast with ASGI) | 3 |
| 451, 302, 420, 562, 690 | Import system, namespace packages, module `__getattr__`, lazy imports (rejected — read why) | 2 |
| 659, 683, 703, 684, 744, 734 | Adaptive interpreter, immortal objects, free-threading, per-interpreter GIL, JIT, subinterpreters stdlib | 2 |
| 517, 518, 621, 660, 735, 740, 751 | Build backends, pyproject metadata, editable installs, dependency groups, attestations, lock files | 0.5, 4 |
| 387 | Backwards compatibility policy | 4 |
| 1 | How PEPs work — read once, then read a live discussion on discuss.python.org | 4 |

## Documentation (the parts that matter)
- Language reference §3 "Data model" — https://docs.python.org/3/reference/datamodel.html — read fully, twice (Tier 1)
- Descriptor HowTo — https://docs.python.org/3/howto/descriptor.html — the best single doc in the Python docs (Tier 0.1)
- `typing` docs + typing spec — https://typing.python.org/en/latest/spec/ (Tier 0.2)
- `asyncio` "Developing with asyncio", "Coroutines and Tasks" (cancellation section), `TaskGroup`, `timeout` (Tier 0.3)
- Import system reference — https://docs.python.org/3/reference/import.html (Tier 2)
- `dis`, `gc`, `sys.getsizeof`, `tracemalloc`, `cProfile`/`pstats` module docs (Tier 0.4, 2)
- Python Developer's Guide — https://devguide.python.org — "Exploring CPython's internals", "Garbage collector design", "Development workflow" (Tier 2, 4)
- ASGI spec (three pages) — https://asgi.readthedocs.io (Tier 3)
- Packaging User Guide — https://packaging.python.org (Tier 0.5, 4)

## Blogs and essays
- Victor Skvortsov, "Python behind the scenes" — https://tenthousandmeters.com/tag/python-behind-the-scenes/ — #1–7, 11, 12, 13 (Tier 2). The best written tour of CPython that exists.
- Nathaniel J. Smith — "Notes on structured concurrency, or: Go statement considered harmful"; "Timeouts and cancellation for humans"; "Some thoughts on asynchronous API design in a post-async/await world" — https://vorpus.org/blog/ (Tier 0.3, 3)
- Hynek Schlawack — https://hynek.me/articles/ — packaging, testing, subclassing, "Semantic Versioning Will Not Save You" (Tier 0.5, 4)
- Brett Cannon — https://snarky.ca — import system, packaging, "unravelling" series on syntax desugaring (Tier 1, 2)
- Claudio Jolowicz, "Hypermodern Python" (Tier 0.5, 4)
- Sam Gross, free-threading design doc (linked from PEP 703) and https://py-free-threading.github.io (Tier 2)
- Guido van Rossum, "Python's tail-call…" no — read his "History of Python" blog for `super()` and MRO (C3) history (Tier 1)
- Raymond Hettinger talks (video): "Super considered super", "Beyond PEP 8", "Modern Python dictionaries" — transcripts exist (Tier 1)
- Łukasz Langa, "Weird Python: …" series and his asyncio talks (Tier 3)

## Source code to read (with prompts in the tier READMEs)
| File | Tier |
|---|---|
| `Lib/functools.py` — `wraps`, `lru_cache`, `singledispatch`, `cached_property` | 0.2, 1 |
| `Lib/dataclasses.py` — `_process_class`, `_create_fn` | 1 |
| `Lib/contextlib.py` — `contextmanager`, `ExitStack` | 1 |
| `Lib/typing.py` — `_GenericAlias`, `Protocol` runtime machinery | 0.2 |
| `Lib/asyncio/tasks.py`, `taskgroups.py`, `timeouts.py`, `base_events.py`, `streams.py` | 0.3, 3 |
| `Lib/concurrent/futures/thread.py`, `process.py` | 3 |
| `Lib/importlib/_bootstrap.py`, `_bootstrap_external.py` | 2 |
| `Python/ceval.c` (`_PyEval_EvalFrameDefault`), `Python/specialize.c` | 2 |
| `Objects/dictobject.c`, `listobject.c`, `typeobject.c` (`type_new`, `slot_tp_getattr_hook`, `_PyType_Lookup`), `obmalloc.c` header | 1, 2 |
| `Objects/descrobject.c` — how `property`, `classmethod` are implemented in C | 0.1 |
| Django `db/models/base.py` (`ModelBase`), `fields/__init__.py` (`Field.contribute_to_class`), `query_utils.py` (`DeferredAttribute`, `Q`), `db/models/query.py` (`QuerySet` laziness, `_fetch_all`) | 0.1, 1 |
| Starlette `applications.py`, `routing.py`, `middleware/base.py`, `requests.py`, `responses.py`, `testclient.py` | 3 |
| uvicorn `protocols/http/h11_impl.py`, `server.py`, `lifespan/on.py` | 3 |
| httpx `_transports/asgi.py`, `_client.py` | 0.3, 3 |
| pydantic `_internal/_model_construction.py` (metaclass), `_generate_schema.py` (skim) | 1 |
| `attrs`, `structlog` repos — as maintained-library exemplars | 4 |
| Trio `_core/_run.py` (skim `Runner`, `CancelScope`) | 3 |

## Order of operations
Don't read ahead of the tier you're in. Each README says what to read *this week* and what to build with it the same week; reading without building is how people finish Fluent Python and still can't write a descriptor.
