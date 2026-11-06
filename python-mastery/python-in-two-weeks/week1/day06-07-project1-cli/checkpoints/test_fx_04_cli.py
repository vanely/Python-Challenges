"""Step 4: the CLI. Spec: steps/04-cli.md.

Tests replace `fetchr.cli._client` (the one factory that builds a real client) with a fake.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import plain
from typer.testing import CliRunner

from fetchr import cli
from fetchr.cache import Cache
from fetchr.models import Issue, IssueState, Repo

runner = CliRunner()


class FakeClient:
    def __init__(self, repos: dict[str, Repo], issues: list[Issue]) -> None:
        self.repos = repos
        self.issue_list = issues
        self.calls: list[tuple[Any, ...]] = []

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def repo(self, owner: str, name: str) -> Repo:
        self.calls.append(("repo", owner, name))
        return self.repos[f"{owner}/{name}"]

    def issues(
        self, owner: str, name: str, state: IssueState = IssueState.OPEN, limit: int | None = None
    ) -> Any:
        self.calls.append(("issues", owner, name, state, limit))
        return iter(self.issue_list[:limit])


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, repo_payload: dict[str, Any]) -> FakeClient:
    httpx_repo = Repo.from_api(repo_payload)  # type: ignore[arg-type]
    flask = Repo.from_api(
        {**repo_payload, "full_name": "pallets/flask", "stargazers_count": 70000, "forks_count": 1}  # type: ignore[typeddict-item]
    )
    issues = [
        Issue.from_api({"number": n, "title": f"t{n}", "user": {"login": "ada"}})
        for n in range(1, 31)
    ]
    client = FakeClient({"encode/httpx": httpx_repo, "pallets/flask": flask}, issues)
    monkeypatch.setattr(cli, "_client", lambda: client)
    return client


def test_repo_json(fake: FakeClient) -> None:
    result = runner.invoke(cli.app, ["repo", "encode/httpx", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data[0]["full_name"] == "encode/httpx"
    assert data[0]["pushed_at"] == "2026-01-02T03:04:05+00:00"


def test_repo_table(fake: FakeClient) -> None:
    result = runner.invoke(cli.app, ["repo", "encode/httpx"])
    assert result.exit_code == 0, result.output
    out = plain(result.stdout)
    assert "13,000" in out
    assert "2026-01-02" in out


def test_repos_sorted(fake: FakeClient) -> None:
    result = runner.invoke(
        cli.app, ["repos", "encode/httpx", "pallets/flask", "--sort", "stars", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert [r["full_name"] for r in json.loads(result.stdout)] == ["pallets/flask", "encode/httpx"]
    result = runner.invoke(
        cli.app, ["repos", "encode/httpx", "pallets/flask", "--sort", "forks", "--json"]
    )
    assert [r["full_name"] for r in json.loads(result.stdout)] == ["encode/httpx", "pallets/flask"]


def test_invalid_sort_is_a_usage_error(fake: FakeClient) -> None:
    result = runner.invoke(cli.app, ["repos", "encode/httpx", "--sort", "bogus"])
    assert result.exit_code == 2
    assert fake.calls == []


@pytest.mark.parametrize("slug", ["nope", "a/b/c", "/x", "x/"])
def test_bad_slug_is_a_usage_error_before_any_request(fake: FakeClient, slug: str) -> None:
    result = runner.invoke(cli.app, ["repos", "encode/httpx", slug])
    assert result.exit_code == 2, result.output
    assert fake.calls == [], "validate every slug before calling GitHub"


def test_issues_json_with_limit_and_state(fake: FakeClient) -> None:
    result = runner.invoke(
        cli.app, ["issues", "encode/httpx", "--limit", "5", "--state", "closed", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert [i["number"] for i in json.loads(result.stdout)] == [1, 2, 3, 4, 5]
    (call,) = fake.calls
    assert call == ("issues", "encode", "httpx", IssueState.CLOSED, 5)
    assert isinstance(call[3], IssueState), "typer should hand you the enum, not a str"


def test_issues_defaults(fake: FakeClient) -> None:
    result = runner.invoke(cli.app, ["issues", "encode/httpx"])
    assert result.exit_code == 0, result.output
    assert fake.calls == [("issues", "encode", "httpx", IssueState.OPEN, 20)]
    out = plain(result.stdout)
    assert "t20" in out and "t21" not in out


@pytest.mark.parametrize("args", [["--state", "bogus"], ["--limit", "0"], ["--limit", "501"]])
def test_issues_option_validation(fake: FakeClient, args: list[str]) -> None:
    result = runner.invoke(cli.app, ["issues", "encode/httpx", *args])
    assert result.exit_code == 2
    assert fake.calls == []


def test_cache_clear(isolated_env: Path) -> None:
    c = Cache()
    c.set("a", 1)
    c.set("b", 2)
    result = runner.invoke(cli.app, ["cache", "clear"])
    assert result.exit_code == 0, result.output
    assert "removed 2" in plain(result.stdout)
    assert list(isolated_env.glob("*.json")) == []


def test_help_lists_commands() -> None:
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("repo", "repos", "issues", "cache"):
        assert cmd in plain(result.stdout)
