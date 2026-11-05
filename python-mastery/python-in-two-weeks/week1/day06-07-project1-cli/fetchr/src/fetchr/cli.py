"""CLI entry point. `fetchr --help`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import httpx
import typer

from fetchr.cache import Cache
from fetchr.client import GitHubClient
from fetchr.models import IssueState, Repo
from fetchr.render import console, issue_table, repo_table, to_json

app = typer.Typer(help="Fetch GitHub repo data.", no_args_is_help=True)
cache_app = typer.Typer(help="Manage the local cache.")
app.add_typer(cache_app, name="cache")

JsonFlag = Annotated[bool, typer.Option("--json", help="Emit JSON instead of a table.")]


def _split(slug: str) -> tuple[str, str]:
    if slug.count("/") != 1:
        raise typer.BadParameter(f"expected owner/name, got {slug!r}")
    owner, name = slug.split("/")
    return owner, name


def _client() -> GitHubClient:
    return GitHubClient(cache=Cache())


def _handle(exc: httpx.HTTPStatusError) -> None:
    console.print(f"[red]HTTP {exc.response.status_code}[/red] for {exc.request.url}")
    raise typer.Exit(code=1)


@app.command()
def repo(slug: str, as_json: JsonFlag = False) -> None:
    """Show one repository (owner/name)."""
    repos(slugs=[slug], as_json=as_json)


@app.command()
def repos(
    slugs: list[str],
    sort: Annotated[str | None, typer.Option(help="stars | forks | issues")] = None,
    as_json: JsonFlag = False,
) -> None:
    """Show several repositories side by side."""
    keys: dict[str, Callable[[Repo], int]] = {
        "stars": lambda r: r.stars,
        "forks": lambda r: r.forks,
        "issues": lambda r: r.open_issues,
    }
    if sort is not None and sort not in keys:
        raise typer.BadParameter(f"--sort must be one of {', '.join(keys)}")
    try:
        with _client() as gh:
            found = [gh.repo(*_split(s)) for s in slugs]
    except httpx.HTTPStatusError as e:
        _handle(e)
    if sort:
        found.sort(key=keys[sort], reverse=True)
    if as_json:
        print(to_json(found))
    else:
        console.print(repo_table(found))


@app.command()
def issues(
    slug: str,
    state: Annotated[str, typer.Option(help="open | closed | all")] = "open",
    limit: Annotated[int, typer.Option(min=1, max=500)] = 20,
    as_json: JsonFlag = False,
) -> None:
    """List issues for a repository (PRs excluded)."""
    if state not in ("open", "closed", "all"):
        raise typer.BadParameter("state must be open, closed or all")
    st: IssueState = state  # type: ignore[assignment]
    try:
        with _client() as gh:
            found = list(gh.issues(*_split(slug), state=st, limit=limit))
    except httpx.HTTPStatusError as e:
        _handle(e)
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
