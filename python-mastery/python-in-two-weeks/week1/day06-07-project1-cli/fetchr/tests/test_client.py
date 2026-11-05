"""No network: monkeypatch httpx.Client.get to return canned responses."""

from typing import Any

import httpx
import pytest

from fetchr.client import GitHubClient


class FakeResponse:
    def __init__(self, data: Any, status: int = 200) -> None:
        self._data = data
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            req = httpx.Request("GET", "https://x")
            resp = httpx.Response(self.status_code)
            raise httpx.HTTPStatusError("err", request=req, response=resp)

    def json(self) -> Any:
        return self._data


def test_issues_paginates_and_skips_prs(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        1: [
            {"number": 1, "title": "a", "user": {"login": "x"}},
            {"number": 2, "title": "pr", "user": {"login": "x"}, "pull_request": {}},
        ],
        2: [{"number": 3, "title": "c", "user": {"login": "y"}}],
        3: [],
    }

    def fake_get(self: httpx.Client, path: str, params: dict[str, Any]) -> FakeResponse:
        return FakeResponse(pages[params["page"]])

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    with GitHubClient() as gh:
        got = list(gh.issues("o", "r"))
    assert [i.number for i in got] == [1, 3]


def test_limit_stops_early(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(self: httpx.Client, path: str, params: dict[str, Any]) -> FakeResponse:
        return FakeResponse([{"number": n, "title": "t", "user": {}} for n in range(100)])

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    with GitHubClient() as gh:
        assert len(list(gh.issues("o", "r", limit=5))) == 5


def test_http_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: FakeResponse({}, 404))
    with GitHubClient() as gh, pytest.raises(httpx.HTTPStatusError):
        gh.repo("o", "missing")
