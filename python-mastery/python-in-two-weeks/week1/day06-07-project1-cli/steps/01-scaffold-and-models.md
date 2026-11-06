# Step 1 — Package scaffold and domain models

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/test_fx_01_models.py`

## What you'll have at the end

- An installable package `fetchr` with a `src/` layout, managed by `uv`.
- `models.py`: typed shapes for the raw GitHub JSON, and the immutable `Repo` and `Issue` objects the rest of the program uses.

## Concepts

### The `src/` layout, and why the package is installed

```
fetchr/
  pyproject.toml
  src/fetchr/__init__.py
  src/fetchr/models.py
  tests/
```

In TypeScript, `import { x } from "./models"` resolves a file path. Python resolves `import fetchr.models` against `sys.path`, a list of directories. `uv sync` installs your project into `.venv` in **editable** mode: it puts a pointer to `src/` on `sys.path`, so edits take effect immediately. It works like `npm link` for your own package.

Why `src/` and not `fetchr/` at the top level? With a top-level package, `import fetchr` from the project root finds the **folder** (the current directory is on `sys.path`), not the installed package. Tests then pass locally and fail once the package is installed, for example when a file is missing from the build. With `src/`, the only way to import `fetchr` is through the installed package, so your tests exercise what users get.

### `pyproject.toml`, line by line

It's `package.json`, `tsconfig.json` and `.eslintrc` in one file. Each tool reads its own `[tool.*]` table.

- `[project]`: name, version, `requires-python`, runtime `dependencies` (like `dependencies` in `package.json`).
- `[project.scripts]`: `fetchr = "fetchr.cli:app"` creates a `fetchr` executable in `.venv` that imports `fetchr.cli` and calls `app()`. This is `"bin"` in `package.json`.
- `[dependency-groups] dev`: tools you need but users don't (`devDependencies`). This is PEP 735; `uv sync` installs the `dev` group by default.
- `[build-system]`: which tool turns the source into an installable wheel. We use hatchling.
- `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`: per-tool config.

### Two kinds of "type" for one JSON object

GitHub returns JSON. You want two different things from it:

1. **A description of the raw shape**, so the type checker knows `data["stargazers_count"]` is an `int`. That's a `TypedDict`, the closest thing Python has to a TS `interface` over a plain object. At runtime it **is** a plain `dict`, with no validation and no methods. `total=False` makes every key optional, like `Partial<...>`. GitHub omits keys and sends `null`, so model that honestly: `description: str | None`.
2. **The domain object** your program passes around: a `@dataclass`. It's a real class with generated `__init__`, `__repr__` and `__eq__`.

The `from_api` classmethod is the boundary between the two. It's the only place that knows GitHub's key names (`stargazers_count`) and defaults. Everything after it works with `repo.stars`. A `@classmethod` receives the class as `cls`, so `cls(...)` builds an instance. It's TS's `static fromApi(data): Repo`, except it also works correctly for subclasses.

### `.get` with a default vs `or`

```python
data.get("stargazers_count", 0)   # 0 only if the key is MISSING
data.get("description") or ""     # "" if the key is missing OR null OR "" (any falsy value)
```

TS's `??` falls back only on `null`/`undefined`. Python's `or` falls back on any falsy value, including `0` and `""`. So use `or` for strings where `null` and `""` mean the same thing, and `.get(key, default)` for numbers, where `0` is a real value you must keep.

### `frozen=True, slots=True`

- `frozen=True`: assigning to a field raises `FrozenInstanceError`. You also get `__hash__`, so instances can go in sets and be dict keys. That's `Readonly<T>`, but enforced at runtime.
- `slots=True`: attributes live in fixed slots instead of a per-instance `__dict__`. It uses less memory, attribute access is a little faster, and a typo like `r.strs = 1` fails instead of silently creating a new attribute.

### Timezones: aware vs naive datetimes

A `datetime` is either **aware** (it has a `tzinfo`, so it is a precise instant) or **naive** (no `tzinfo`: "3 PM somewhere"). Comparing or subtracting a naive and an aware datetime raises `TypeError`. GitHub sends `"2026-01-02T03:04:05Z"`. Since Python 3.11, `datetime.fromisoformat` understands the `Z` and returns an aware UTC datetime. Older tutorials do `.replace("Z", "+00:00")` first; you don't need to.

When a timestamp is missing, return `None`, not `datetime.min`. `datetime.min` is naive, so a later `repo.pushed_at > cutoff` crashes. It's also a lie: "pushed in year 1".

### `StrEnum` for a closed set of strings

```python
class IssueState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"
```

TS would write `type IssueState = "open" | "closed" | "all"`. Python's equivalent `Literal["open", "closed", "all"]` exists only for the type checker. At runtime, a `str` from the command line is just a `str`, and you need a `# type: ignore` to treat it as the literal. A `StrEnum` exists at runtime: `IssueState("open")` validates and converts. Each member **is** a `str` (`IssueState.OPEN == "open"`), so it can go straight into URL params. typer turns an enum parameter into a validated `--state` choice for free (step 4).

### `from __future__ import annotations`

It makes every annotation a lazily evaluated string. That's why `def from_api(cls, data: RepoPayload) -> Repo:` can name `Repo` inside `Repo`'s own body. Put it at the top of every module you write in this project. The one place it can hurt is a library that reads annotations at runtime; you'll see that with FastAPI in docpipe.

## Build

### 1. `pyproject.toml`

Replace the generated file with:

```toml
[project]
name = "fetchr"
version = "0.1.0"
description = "Fetch and display GitHub repo data"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "typer>=0.12", "rich>=13"]

[project.scripts]
fetchr = "fetchr.cli:app"

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6", "mypy>=1.12"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

Then:

```bash
uv sync
uv run python -c "import fetchr; print(fetchr.__file__)"   # .../fetchr/src/fetchr/__init__.py
```

`fetchr.cli` doesn't exist yet, so the `fetchr` command will fail until step 4. That's expected.

Set `src/fetchr/__init__.py` to just a docstring and `__version__ = "0.1.0"`; this deletes the generated `main()`. You'll re-export the models from it at the end of this step. Also run `mkdir tests`, because `uv init` doesn't create it and your own tests go there from step 3.

### 2. `src/fetchr/models.py`

```python
"""Domain models. Frozen dataclasses built from TypedDict-shaped API payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypedDict


class IssueState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


class RepoPayload(TypedDict, total=False):
    """Subset of GET /repos/{owner}/{repo}. total=False: keys may be missing."""

    full_name: str
    description: str | None
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    language: str | None
    html_url: str
    pushed_at: str | None


class IssuePayload(TypedDict, total=False):
    number: int
    title: str
    state: str
    created_at: str
    html_url: str
    user: dict[str, object] | None
    pull_request: dict[str, object]  # present only when the "issue" is a PR


@dataclass(frozen=True, slots=True)
class Repo:
    full_name: str
    description: str
    stars: int
    forks: int
    open_issues: int
    language: str
    url: str
    pushed_at: datetime | None

    @classmethod
    def from_api(cls, data: RepoPayload) -> Repo:
        return cls(
            full_name=data["full_name"],
            description=data.get("description") or "",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            language=data.get("language") or "—",
            url=data.get("html_url", ""),
            pushed_at=parse_dt(data.get("pushed_at")),
        )


def parse_dt(value: str | None) -> datetime | None:
    """GitHub timestamps are UTC with a trailing Z. Always returns an aware datetime (or None)."""
    if not value:
        return None
    return datetime.fromisoformat(value)
```

Notes:
- `data["full_name"]` uses brackets, not `.get`. A repo without a name is a broken payload. Failing loudly with `KeyError` here beats a blank row three layers later.
- `language` falls back to `"—"` for display. That's a presentation choice leaking into the model. It's acceptable in a 300-line tool, but write down in `NOTES.md` where you'd put it in a bigger one.

### 3. Your turn: `Issue`

Add a frozen, slotted `Issue` dataclass with fields `number: int`, `title: str`, `state: str`, `author: str`, `created_at: datetime | None`, `url: str`, and a `from_api(cls, data: IssuePayload) -> Issue` classmethod:

- `number` and `title` are required (brackets);
- `state` defaults to `"open"`; `url` defaults to `""`;
- `author` is `user["login"]`. GitHub sends `"user": null` for deleted accounts, and the key may be missing entirely. In both cases use `"?"`;
- `created_at` goes through `parse_dt`.

Then re-export `Issue`, `IssueState` and `Repo` from `fetchr/__init__.py` with an `__all__`.

<details><summary>Hint: the user</summary>

`data.get("user")` is `dict | None`, and `None.get(...)` raises. Normalise first: `user = data.get("user") or {}`. Then `user.get("login", "?")` is an `object` (that's how the TypedDict declares it), so wrap it in `str(...)` to satisfy mypy.
</details>

### 4. Look at what you built

```bash
uv run python
>>> from fetchr import Repo
>>> r = Repo.from_api({"full_name": "a/b", "pushed_at": "2026-01-02T03:04:05Z"})
>>> r
>>> r.pushed_at.tzinfo
>>> r.stars = 5          # predict the exception first
>>> {r, r}               # why does this work?
>>> r.__dict__           # and why does this fail?
```

## Checkpoint

```bash
uv run pytest ../checkpoints/test_fx_01_models.py
uv run mypy src
uv run ruff check . && uv run ruff format .
```

## Pitfalls

- **Mutable defaults.** `tags: list[str] = []` on a dataclass raises at class creation. Use `field(default_factory=list)`. Dataclasses refuse here because a shared mutable default is the classic Python bug.
- **`or` on numbers.** `data.get("stargazers_count") or 0` happens to work, but `x or default` on a number that can legitimately be `0` is a habit that will bite you. Use `.get(key, default)`.
- **Validating with TypedDict.** A TypedDict validates nothing at runtime. If you need validation at a trust boundary, that's Pydantic (Day 10). For a CLI reading a well-known API, `from_api` with explicit defaults is enough.
- **Naive datetimes.** `datetime.now()` is naive and `datetime.now(UTC)` is aware. Mixing them fails only when you compare them, often far from where the naive one was created.

## Explain it back

1. Why does the `src/` layout make tests more trustworthy? What exactly would `import fetchr` find without it?
2. What does `total=False` change, for mypy and at runtime?
3. Give a payload where `data.get("x", d)` and `data.get("x") or d` return different values.
4. Why can a frozen dataclass be put in a set, while a regular one (with `eq=True`) can't?
5. Why is `datetime.min` a bad stand-in for "unknown"? Name two separate problems.
6. `Literal["open", "closed"]` vs `StrEnum`: what exists at runtime in each case?
