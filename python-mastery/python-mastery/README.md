# Python Mastery Path

For an engineer who already writes production Python (Django/DRF) and competitive-programming Python,
and wants to close the gap to genuine mastery: the runtime, the data model, typing, async, performance,
and library-grade engineering. Nothing here teaches syntax.

## Time budget

| Tier | Focus | Weeks @ 8–10 hrs/wk |
|---|---|---|
| 0 | Foundations you were never forced to learn: descriptors/metaclasses, typed decorators, async cancellation, profiling, packaging | 5–6 |
| 1 | Data-model fluency (Fluent Python, deeply) + toy ORM v2 | 5–6 |
| 2 | The runtime: bytecode, import system, memory, GIL, native extensions, performance lab | 6–8 |
| 3 | Async and systems: build an ASGI framework, mixed-executor service, contextvars, structured concurrency | 4–6 |
| 4 | Library authorship: publish a real package, land upstream PRs | 8+ (overlaps) |
| 5 | Teach it: written explainers | ongoing |

Roughly 7–9 months to the "strongest Python engineer on the team" level. Tiers 4–5 never really end.

## How each module works

Every module folder has:
- `README.md` — objectives, readings (where to find them + summaries of the parts that matter), the analysis prompts, and the build spec
- `copy/` — annotated reference code to **type out by hand** and then modify; each file runs and is `mypy --strict` clean unless the README says otherwise
- a project folder with a spec and, where it exists, a tested reference implementation to diff against **after** you build your own

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
```bash
uv python install 3.12 3.13
uv venv && source .venv/bin/activate
uv pip install mypy ruff pytest pytest-asyncio httpx numpy polars cython nox uvicorn starlette pydantic py-spy scalene
```
Rust for Tier 2: `curl https://sh.rustup.rs -sSf | sh` and `uv pip install maturin`.

## Rules
1. `mypy --strict` and `ruff check` on everything you write. No exceptions for "it's just a script."
2. Type out `copy/` files; then break them on purpose and predict the failure before running.
3. Read the linked source *before* the README summary tells you what it does. Summaries are for checking, not replacing.
4. Every project ends with a short written retrospective (`NOTES.md`). Mastery is mostly the ability to explain.
