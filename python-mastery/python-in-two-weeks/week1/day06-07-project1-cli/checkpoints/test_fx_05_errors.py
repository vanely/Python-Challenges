"""Step 5: failure modes. Spec: steps/05-harden.md.

Real GitHubClient + fake transport, driven through the CLI: every failure a user can hit ends
in one readable line on stderr and exit code 1, never a traceback.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from conftest import FakeGitHub, plain
from typer.testing import CliRunner

from fetchr import cli
from fetchr.client import GitHubClient, RateLimitError

Fake = Callable[[Callable[[httpx.Request], httpx.Response]], FakeGitHub]
runner = CliRunner()
RESET = 1_800_000_000  # 2027-01-15T08:00:00Z


def _use(monkeypatch: pytest.MonkeyPatch, transport: httpx.BaseTransport) -> None:
    monkeypatch.setattr(cli, "_client", lambda: GitHubClient(transport=transport))


def _rate_limited(req: httpx.Request) -> httpx.Response:
    return httpx.Response(
        403,
        headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(RESET)},
        json={"message": "API rate limit exceeded"},
    )


def test_client_raises_rate_limit_error(fake_github: Fake) -> None:
    gh_fake = fake_github(_rate_limited)
    with GitHubClient(transport=gh_fake.transport) as gh, pytest.raises(RateLimitError) as ei:
        gh.repo("o", "r")
    assert ei.value.reset_at == datetime.fromtimestamp(RESET, tz=UTC)


def test_plain_403_is_not_a_rate_limit(fake_github: Fake) -> None:
    gh_fake = fake_github(
        lambda req: httpx.Response(403, headers={"x-ratelimit-remaining": "42"}, json={})
    )
    with GitHubClient(transport=gh_fake.transport) as gh, pytest.raises(httpx.HTTPStatusError):
        gh.repo("o", "r")


def _assert_clean_failure(result: Any, *needles: str) -> None:
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit), f"traceback leaked: {result.exception!r}"
    assert "Traceback" not in result.output
    for needle in needles:
        assert needle.lower() in plain(result.stderr).lower(), result.stderr
    assert result.stdout == "", "errors go to stderr so stdout stays parseable"


def test_404_is_one_line_exit_1(monkeypatch: pytest.MonkeyPatch, fake_github: Fake) -> None:
    _use(monkeypatch, fake_github(lambda req: httpx.Response(404, json={})).transport)
    result = runner.invoke(cli.app, ["repo", "o/missing", "--json"])
    _assert_clean_failure(result, "404")


def test_rate_limit_message(monkeypatch: pytest.MonkeyPatch, fake_github: Fake) -> None:
    _use(monkeypatch, fake_github(_rate_limited).transport)
    result = runner.invoke(cli.app, ["issues", "o/r"])
    _assert_clean_failure(result, "rate limit", "GITHUB_TOKEN")


def test_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=req)

    _use(monkeypatch, httpx.MockTransport(refuse))
    result = runner.invoke(cli.app, ["repo", "o/r"])
    _assert_clean_failure(result, "network")


def test_timeout_is_a_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def slow(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=req)

    _use(monkeypatch, httpx.MockTransport(slow))
    result = runner.invoke(cli.app, ["repo", "o/r"])
    _assert_clean_failure(result, "network")


def test_error_on_a_later_page_still_clean(
    monkeypatch: pytest.MonkeyPatch, fake_github: Fake
) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.params["page"] == "1":
            return httpx.Response(200, json=[{"number": n, "title": "t"} for n in range(100)])
        return httpx.Response(502, json={})

    _use(monkeypatch, fake_github(handler).transport)
    result = runner.invoke(cli.app, ["issues", "o/r", "--limit", "150", "--json"])
    _assert_clean_failure(result, "502")


def test_success_still_works_end_to_end(
    monkeypatch: pytest.MonkeyPatch, fake_github: Fake, repo_payload: dict[str, Any]
) -> None:
    _use(monkeypatch, fake_github(lambda req: httpx.Response(200, json=repo_payload)).transport)
    result = runner.invoke(cli.app, ["repo", "encode/httpx", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)[0]["stars"] == 13000
