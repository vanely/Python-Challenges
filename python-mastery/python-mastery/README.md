# Python Mastery Path

Stage 3 of the [roadmap](../README.md). It's for someone who has finished Stage 2 ([`../django-and-drf/`](../django-and-drf/README.md)) or already ships production Django/DRF, and wants to close the gap to genuine mastery: the runtime, the data model, typing, async, performance, and library-grade engineering. Nothing here teaches syntax. Several modules open by taking apart Django internals you used in Stage 2 (`ModelBase`, `DeferredAttribute`, `QuerySet` laziness, middleware).

## Time budget

| Tier | Focus | Weeks @ 8–10 hrs/wk |
|---|---|---|
| 0 | Foundations you were never forced to learn: descriptors/metaclasses, typed decorators, async cancellation, profiling, packaging | 6–8 |
| 1 | Data-model fluency (Fluent Python, deeply) + toy ORM v2 | 8–10 |
| 2 | The runtime: bytecode, import system, memory, GIL, native extensions, performance lab | 8–10 |
| 3 | Async and systems: build an ASGI framework, mixed-executor service, contextvars, structured concurrency | 6–8 |
| 4 | Library authorship: publish a real package, land upstream PRs | a separate, open-ended goal |
| 5 | Teach it: written explainers | ongoing, alongside everything |

Tiers 0–3 take roughly 9–12 months. The build tasks are the expensive part. Reimplementing `lru_cache` or adding relations and lazy querysets to tinyorm is 10–20 hours each, not an afternoon. Tier 4 depends on other people's review cycles, so treat it as its own goal rather than a block of weeks. In Tier 2, pick **one** of Cython or Rust/PyO3 for the extension work; the lesson about where the time goes is the same.

## How each module works

Every module folder has:
- `README.md` — objectives, readings (where to find them + summaries of the parts that matter), the analysis prompts, and the build spec
- `copy/` — annotated reference code to **type out by hand** and then modify; each file runs and is `mypy --strict` clean unless the README says otherwise
- a project folder with a spec, `steps/`, and `checkpoints/` you didn't write. A finished implementation, where one exists, is under `reference/`. Open it after your checkpoints pass. `mixed-executor-service/` has no reference on purpose: the bugs are the lesson. `rust-ext/` is a scaffold you extend, not a solution you are hiding from.

Rhythm per week (~9 hrs): 2 hrs reading, 2 hrs copying + modifying, 2 hrs reading library/CPython source against the prompts, 3 hrs building.

## Layout

```
tier0-foundations/
  01-descriptors-metaclasses/   how Django's Model/Field actually work → build tinyorm
  02-typed-decorators/          ParamSpec, overload, Protocol, generics → typed_utils
  03-async-cancellation/        cancellation semantics, TaskGroup, shutdown → rate-limited fetcher
  04-profiling/                 cProfile, py-spy, tracemalloc, scalene → optimisation lab
  05-packaging/                 pyproject, nox, CI, TestPyPI → publish pkgtemplate
tier1-data-model/               Fluent Python reading map, dunder deep-dives → tinyorm v2 (relations, lazy querysets), lru_cache & dataclass reimplementations
tier2-runtime-performance/      dis/bytecode, import hooks, __slots__, GIL, Cython, Rust/PyO3 → perflab
tier3-async-systems/            microasgi (your own Starlette), mixed executors, contextvars, trio contrast
tier4-library-authorship/       release engineering, upstream contribution playbook
tier5-teach/                    explainer briefs
reading/                        the master reading list with per-chapter summaries
```

## Setup
The course runs on **Python 3.12**, pinned by `../.python-version`. Projects with a `pyproject.toml` (tinyorm, fetchd, pkgtemplate, microasgi, rust-ext) use `uv sync` then `uv run ...`. For the loose `copy/` scripts, make one scratch environment here:

```bash
uv python install 3.12 3.13t
uv venv                                   # Python 3.12 from ../.python-version
source .venv/Scripts/activate             # Windows/Git Bash; macOS/Linux: source .venv/bin/activate
uv pip install mypy ruff pytest pytest-asyncio httpx numpy polars cython nox uvicorn starlette pydantic py-spy scalene
```

Free-threading experiments run with `uv run --python 3.13t ...`. Rust for Tier 2 on Windows: install with `winget install Rustlang.Rustup` (it needs the MSVC build tools, which the installer offers); on macOS/Linux use `curl https://sh.rustup.rs -sSf | sh`. Then `uv pip install maturin`.

Some demos are POSIX-only (Unix signal handlers, `fork`). Each one says so and shows its Windows fallback.

## Rules
1. `mypy --strict` and `ruff check` on everything you write. No exceptions for "it's just a script."
2. Type out `copy/` files; then break them on purpose and predict the failure before running.
3. Read the linked source *before* the README summary tells you what it does. Summaries are for checking, not replacing.
4. Every project ends with a short written retrospective in [`NOTES.md`](NOTES.md). Mastery is mostly the ability to explain.
