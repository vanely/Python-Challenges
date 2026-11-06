"""Step 3: the client. Spec: steps/03-client.md.

GitHubClient must accept `transport=` and pass it to httpx.Client, so these tests can answer
requests from a function instead of the network.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from conftest import FakeGitHub, issue

from fetchr.cache import Cache
from fetchr.client import GitHubClient
from fetchr.models import IssueState

Fake = Callable[[Callable[[httpx.Request], httpx.Response]], FakeGitHub]


def test_repo_request_shape(fake_github: Fake, repo_payload: dict[str, Any]) -> None:
    gh_fake = fake_github(lambda req: httpx.Response(200, json=repo_payload))
    with GitHubClient(transport=gh_fake.transport) as gh:
        r = gh.repo("encode", "httpx")
    assert r.full_name == "encode/httpx"
    (req,) = gh_fake.requests
    assert req.url.host == "api.github.com"
    assert req.url.path == "/repos/encode/httpx"
    assert req.headers["accept"] == "application/vnd.github+json"
    assert req.headers["user-agent"]
    assert "authorization" not in req.headers


def test_token_from_argument_or_env(
    fake_github: Fake, repo_payload: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    gh_fake = fake_github(lambda req: httpx.Response(200, json=repo_payload))
    with GitHubClient(token="t0k", transport=gh_fake.transport) as gh:
        gh.repo("o", "r")
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    with GitHubClient(transport=gh_fake.transport) as gh:
        gh.repo("o", "r")
    assert [r.headers["authorization"] for r in gh_fake.requests] == [
        "Bearer t0k",
        "Bearer from-env",
    ]


def test_http_errors_raise(fake_github: Fake) -> None:
    gh_fake = fake_github(lambda req: httpx.Response(404, json={"message": "Not Found"}))
    with GitHubClient(transport=gh_fake.transport) as gh, pytest.raises(httpx.HTTPStatusError):
        gh.repo("o", "missing")


def test_responses_are_cached_and_errors_are_not(
    fake_github: Fake, repo_payload: dict[str, Any], tmp_path: Path
) -> None:
    status = iter([500, 200, 200])
    gh_fake = fake_github(lambda req: httpx.Response(next(status), json=repo_payload))
    cache = Cache(directory=tmp_path / "c")
    with GitHubClient(cache=cache, transport=gh_fake.transport) as gh:
        with pytest.raises(httpx.HTTPStatusError):
            gh.repo("o", "r")
        gh.repo("o", "r")
        gh.repo("o", "r")
    assert len(gh_fake.requests) == 2, "500 not cached; second success served from cache"


def _pages(pages: dict[int, list[dict[str, Any]]]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages.get(int(req.url.params["page"]), []))

    return handler


def test_issues_is_a_generator() -> None:
    assert inspect.isgeneratorfunction(GitHubClient.issues)


def test_issues_paginates_and_skips_pull_requests(fake_github: Fake) -> None:
    full_page = [issue(n, pr=(n % 10 == 0)) for n in range(1, 101)]
    gh_fake = fake_github(_pages({1: full_page, 2: [issue(101), issue(102)]}))
    with GitHubClient(transport=gh_fake.transport) as gh:
        got = [i.number for i in gh.issues("o", "r")]
    assert got == [n for n in range(1, 103) if n % 10 != 0]
    params = [dict(r.url.params) for r in gh_fake.requests]
    assert [p["page"] for p in params] == ["1", "2"], "a short page is the last page"
    assert all(p["per_page"] == "100" and p["state"] == "open" for p in params)


def test_empty_repo_makes_one_request(fake_github: Fake) -> None:
    gh_fake = fake_github(_pages({}))
    with GitHubClient(transport=gh_fake.transport) as gh:
        assert list(gh.issues("o", "r")) == []
    assert len(gh_fake.requests) == 1


def test_exactly_full_last_page_needs_one_more_request(fake_github: Fake) -> None:
    gh_fake = fake_github(_pages({1: [issue(n) for n in range(100)]}))
    with GitHubClient(transport=gh_fake.transport) as gh:
        assert len(list(gh.issues("o", "r"))) == 100
    assert len(gh_fake.requests) == 2


def test_issues_is_lazy_and_limit_stops_early(fake_github: Fake) -> None:
    full = {p: [issue(n) for n in range((p - 1) * 100, p * 100)] for p in range(1, 6)}
    gh_fake = fake_github(_pages(full))
    with GitHubClient(transport=gh_fake.transport) as gh:
        it = gh.issues("o", "r", limit=150)
        assert gh_fake.requests == [], "creating the generator must not fetch"
        next(it)
        assert len(gh_fake.requests) == 1
        assert len(list(it)) == 149
    assert len(gh_fake.requests) == 2, "stop fetching once limit is reached"


def test_state_is_sent(fake_github: Fake) -> None:
    gh_fake = fake_github(_pages({}))
    with GitHubClient(transport=gh_fake.transport) as gh:
        list(gh.issues("o", "r", state=IssueState.CLOSED))
    assert gh_fake.requests[0].url.params["state"] == "closed"


def test_exiting_closes_the_http_client(fake_github: Fake, repo_payload: dict[str, Any]) -> None:
    gh_fake = fake_github(lambda req: httpx.Response(200, json=repo_payload))
    with GitHubClient(transport=gh_fake.transport) as gh:
        pass
    with pytest.raises(RuntimeError):
        gh.repo("o", "r")  # httpx refuses to send on a closed client
