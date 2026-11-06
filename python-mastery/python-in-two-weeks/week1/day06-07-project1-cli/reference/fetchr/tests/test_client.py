"""No network: GitHubClient takes a transport, and httpx.MockTransport answers from a function."""

from typing import Any

import httpx
import pytest

from fetchr.client import GitHubClient


def _issue(n: int, **extra: Any) -> dict[str, Any]:
    return {"number": n, "title": str(n), "user": {"login": "x"}, **extra}


def test_issues_paginates_and_skips_prs() -> None:
    pages = {1: [_issue(n, **({"pull_request": {}} if n == 2 else {})) for n in range(100)]}
    pages[2] = [_issue(100)]
    seen: list[int] = []

    def handler(req: httpx.Request) -> httpx.Response:
        page = int(req.url.params["page"])
        seen.append(page)
        return httpx.Response(200, json=pages[page])

    with GitHubClient(transport=httpx.MockTransport(handler)) as gh:
        got = [i.number for i in gh.issues("o", "r")]
    assert 2 not in got and len(got) == 100
    assert seen == [1, 2]


def test_limit_stops_early() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_issue(n) for n in range(100)])

    with GitHubClient(transport=httpx.MockTransport(handler)) as gh:
        assert len(list(gh.issues("o", "r", limit=5))) == 5


def test_http_error_propagates() -> None:
    transport = httpx.MockTransport(lambda req: httpx.Response(404, json={}))
    with GitHubClient(transport=transport) as gh, pytest.raises(httpx.HTTPStatusError):
        gh.repo("o", "missing")
