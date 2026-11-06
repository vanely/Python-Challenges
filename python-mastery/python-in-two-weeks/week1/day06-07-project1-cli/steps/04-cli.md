# Step 4 — The CLI: typer commands, rich output, JSON

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/test_fx_04_cli.py`

## What you'll have at the end

`uv run fetchr repo encode/httpx` prints a table. `--json` prints machine-readable output. Bad input gets a usage error **before** any network call.

## Concepts

### typer: the function signature is the CLI

```python
@app.command()
def issues(
    slug: str,                                                    # positional argument
    limit: Annotated[int, typer.Option(min=1, max=500)] = 20,    # --limit, validated range
    as_json: Annotated[bool, typer.Option("--json")] = False,    # flag named --json
) -> None:
    """List issues for a repository (PRs excluded)."""            # becomes --help text
```

- A parameter **without** a default is a positional argument; one **with** a default is an `--option`.
- `Annotated[T, typer.Option(...)]` attaches CLI metadata without changing the Python type, so mypy still sees `int`. (`Annotated` is the standard way to hang metadata on a type; FastAPI uses it the same way on Day 10.)
- `list[str]` with no default is a variadic positional: `fetchr repos a/b c/d e/f`.
- **An `Enum`-typed parameter becomes a choice.** typer shows the allowed values in `--help`, rejects anything else with exit code 2, and hands your function the **enum member**, not a string. That's why `IssueState` and `SortKey` are enums: the validation happens before your code runs, and your code never needs a `# type: ignore`.
- `typer.Typer()` instances nest: `app.add_typer(cache_app, name="cache")` gives you `fetchr cache clear`.

### Exit codes are an API

Scripts and CI read them. The convention typer follows (inherited from click, which older typer versions were built on):
- `0`: success.
- `1`: the command ran and failed (network down, 404, rate limited). Step 5.
- `2`: **usage error**: bad arguments, the user's fault. `raise typer.BadParameter("...")` produces this, with the usage line.

### stdout is data, stderr is talk

`fetchr repos ... --json | jq '.[0].stars'` only works if stdout contains **nothing but JSON**. Tables and JSON go to stdout. Errors, progress and warnings go to stderr: `Console(stderr=True, soft_wrap=True)`. When rich isn't writing to a terminal (a pipe, a log file, a test runner), it hard-wraps at 80 columns. That would split an error message, URL included, across lines; `soft_wrap=True` leaves long lines whole. For JSON, use plain `print(to_json(...))`, not rich. Rich would add colour codes and wrap long lines.

### Validate everything before doing anything

`fetchr repos encode/httpx typo` must fail with exit code 2 **without** fetching `encode/httpx` first. Parse every slug, then open the client. That's cheaper for the user, and it means a usage error never costs rate limit.

### `dataclasses.asdict` + `json.dumps(default=...)`

`asdict` recursively turns a dataclass into a dict. `json.dumps` doesn't know `datetime`, so pass `default=`: a function json calls for any object it can't serialise. Return something it can (an ISO string), or raise `TypeError`. Don't `default=str`: it silently serialises *anything*, including objects you didn't mean to output.

### One factory, so tests can swap the client

```python
def _client() -> GitHubClient:
    """The one place a real client is built. Tests replace this function."""
    return GitHubClient(cache=Cache())
```

Commands call `_client()`, never `GitHubClient(...)` directly. A test does `monkeypatch.setattr(cli, "_client", lambda: FakeClient(...))`. This works because `repos` looks up the global name `_client` **when it runs**, in the `fetchr.cli` module namespace, which is exactly what `monkeypatch.setattr(cli, ...)` replaces.

## Build

### 1. `render.py`

```python
"""Output: rich tables or JSON."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table

from fetchr.models import Issue, Repo

console = Console()
err_console = Console(stderr=True, soft_wrap=True)


def _default(o: object) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"not serialisable: {type(o).__name__}")


def to_json(items: Iterable[Any]) -> str:
    rows = [
        dataclasses.asdict(i) if dataclasses.is_dataclass(i) and not isinstance(i, type) else i
        for i in items
    ]
    return json.dumps(rows, indent=2, default=_default)


def _date(d: datetime | None) -> str:
    return d.date().isoformat() if d else "—"


def repo_table(repos: Iterable[Repo]) -> Table:
    t = Table(title="Repositories")
    for col in ("Repo", "Stars", "Forks", "Issues", "Lang", "Pushed"):
        t.add_column(col, justify="right" if col in {"Stars", "Forks", "Issues"} else "left")
    for r in repos:
        t.add_row(
            r.full_name,
            f"{r.stars:,}",
            f"{r.forks:,}",
            str(r.open_issues),
            r.language,
            _date(r.pushed_at),
        )
    return t
```

`dataclasses.is_dataclass(x)` is true for dataclass **classes** as well as instances, which is why there's an `isinstance(i, type)` check. `f"{13000:,}"` gives `13,000`.

Add `issue_table(issues)` yourself: columns `#`, `Title` (`max_width=60`), `Author`, `Opened`.

### 2. `cli.py`

```python
"""CLI entry point. `fetchr --help`."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated

import typer

from fetchr.cache import Cache
from fetchr.client import GitHubClient
from fetchr.models import IssueState, Repo
from fetchr.render import console, issue_table, repo_table, to_json

app = typer.Typer(help="Fetch GitHub repo data.", no_args_is_help=True)
cache_app = typer.Typer(help="Manage the local cache.")
app.add_typer(cache_app, name="cache")

JsonFlag = Annotated[bool, typer.Option("--json", help="Emit JSON instead of a table.")]


class SortKey(StrEnum):
    STARS = "stars"
    FORKS = "forks"
    ISSUES = "issues"


SORT_KEYS: dict[SortKey, Callable[[Repo], int]] = {
    SortKey.STARS: lambda r: r.stars,
    SortKey.FORKS: lambda r: r.forks,
    SortKey.ISSUES: lambda r: r.open_issues,
}


def _split(slug: str) -> tuple[str, str]:
    owner, sep, name = slug.partition("/")
    if not sep or not owner or not name or "/" in name:
        raise typer.BadParameter(f"expected owner/name, got {slug!r}")
    return owner, name


def _client() -> GitHubClient:
    """The one place a real client is built. Tests replace this function."""
    return GitHubClient(cache=Cache())


@app.command()
def repo(slug: str, as_json: JsonFlag = False) -> None:
    """Show one repository (owner/name)."""
    repos(slugs=[slug], sort=None, as_json=as_json)


@app.command()
def repos(
    slugs: list[str],
    sort: Annotated[SortKey | None, typer.Option(help="Sort descending by this field.")] = None,
    as_json: JsonFlag = False,
) -> None:
    """Show several repositories side by side."""
    pairs = [_split(s) for s in slugs]  # validate every slug before any network call
    with _client() as gh:
        found = [gh.repo(owner, name) for owner, name in pairs]
    if sort is not None:
        found.sort(key=SORT_KEYS[sort], reverse=True)
    if as_json:
        print(to_json(found))
    else:
        console.print(repo_table(found))


if __name__ == "__main__":
    app()
```

Notes:
- `str.partition("/")` always returns a 3-tuple. `slug.split("/")` with unpacking would raise `ValueError` on `"a/b/c"`, a traceback instead of a usage error.
- `repo` calls `repos` as a plain function. Decorated typer commands are still ordinary Python functions.
- The `dict` of key functions replaces an `if/elif` chain. Adding a sort key is now one line, and mypy checks that every value takes a `Repo` and returns an `int`.

### 3. Your turn: `issues` and `cache clear`

`issues SLUG [--state open|closed|all] [--limit N] [--json]`:
- `--state` is an `IssueState` option, default `IssueState.OPEN`;
- `--limit` is between 1 and 500, default 20;
- validate the slug first (exit 2 on a bad one, with no client created);
- pass `state` and `limit` to `gh.issues(owner, name, state=..., limit=...)`, and consume it **inside** the `with`;
- output a table via `issue_table`, or JSON.

`cache clear` (a command on `cache_app`, named `"clear"`) deletes everything in the default cache and prints `removed N cached file(s)`.

### 4. Use it

```bash
uv run fetchr --help
uv run fetchr issues --help                         # see the state choices
uv run fetchr repo encode/httpx
uv run fetchr repos encode/httpx pallets/flask --sort stars
uv run fetchr issues encode/httpx --limit 5 --json
uv run fetchr repos encode/httpx bad-slug; echo "exit: $?"
uv run fetchr issues encode/httpx --state maybe; echo "exit: $?"
```

## Checkpoint

```bash
uv run pytest ../checkpoints/test_fx_04_cli.py
uv run pytest ../checkpoints/test_fx_0{1,2,3,4}_*.py  # 01–04 together (05 can't even import yet)
uv run mypy src && uv run ruff check .
```

## Pitfalls

- **`str` options with a manual `if state not in (...)` check.** It works, but you write the validation yourself, the help text doesn't list the choices, and you need a `# type: ignore` to call a function that takes `IssueState`.
- **Printing JSON with rich.** `console.print(json_str)` highlights it and may wrap it, so it isn't valid JSON for `jq` any more. Use `print`, or `console.print_json` only for humans.
- **Building the real client in every command.** Then tests have to patch `GitHubClient` in two places. One factory function is one seam.
- **Consuming the generator after `with`.** `found = gh.issues(...)` inside the block and `list(found)` after it gives `RuntimeError: Cannot send a request, as the client has been closed.`

## Explain it back

1. Which exit code does a typo in `--state` produce, and which part of the stack produces it? Why is that a different code from "repo not found"?
2. Why must `repos` validate *all* slugs before opening the client?
3. Why does `monkeypatch.setattr(cli, "_client", ...)` affect `repos`? Would it still work if `repos` did `from fetchr.cli import _client` inside the function? Would it work with a default argument `client_factory=_client`?
4. `default=str` vs a `default` function that raises: what bug does the strict version catch?
5. Why does JSON go to stdout with plain `print`, while errors go to a stderr console?
