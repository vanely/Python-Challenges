"""CLI entry point. `fetchr --help`."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from typing import Annotated, NoReturn

import httpx
import typer

from fetchr.cache import Cache
from fetchr.client import GitHubClient, RateLimitError
from fetchr.models import IssueState, Repo
from fetchr.render import console, err_console, issue_table, repo_table, to_json

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


def _fail(message: str) -> NoReturn:
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(code=1)


@contextmanager
def _github_errors() -> Iterator[None]:
    """Turn the failures a user can cause or hit into one line and exit code 1."""
    try:
        yield
    except RateLimitError as e:
        _fail(f"{e}. Set GITHUB_TOKEN to raise the limit.")
    except httpx.HTTPStatusError as e:
        _fail(f"HTTP {e.response.status_code} for {e.request.url}")
    except httpx.RequestError as e:
        _fail(f"network error talking to {e.request.url}: {e}")


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
    with _github_errors(), _client() as gh:
        found = [gh.repo(owner, name) for owner, name in pairs]
    if sort is not None:
        found.sort(key=SORT_KEYS[sort], reverse=True)
    if as_json:
        print(to_json(found))
    else:
        console.print(repo_table(found))


@app.command()
def issues(
    slug: str,
    state: Annotated[IssueState, typer.Option(help="Which issues to list.")] = IssueState.OPEN,
    limit: Annotated[int, typer.Option(min=1, max=500)] = 20,
    as_json: JsonFlag = False,
) -> None:
    """List issues for a repository (PRs excluded)."""
    owner, name = _split(slug)
    with _github_errors(), _client() as gh:
        found = list(gh.issues(owner, name, state=state, limit=limit))
    if as_json:
        print(to_json(found))
    else:
        console.print(issue_table(found))


@cache_app.command("clear")
def cache_clear() -> None:
    """Delete all cached responses."""
    n = Cache().clear()
    console.print(f"removed {n} cached file(s)")


if __name__ == "__main__":
    app()
