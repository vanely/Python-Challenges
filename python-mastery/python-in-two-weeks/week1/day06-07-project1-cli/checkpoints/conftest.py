"""Shared fixtures for the fetchr checkpoints. Run from your fetchr/ folder:

    uv run pytest ../checkpoints/test_fx_01_models.py

Nothing here touches the network or your real ~/.cache.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def plain(text: str) -> str:
    """Strip terminal styling. rich adds it when your environment forces colour (FORCE_COLOR)."""
    return _ANSI.sub("", text)


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Every test gets its own cache dir and no GitHub token from your shell."""
    cache_dir = tmp_path / "fetchr-cache"
    monkeypatch.setenv("FETCHR_CACHE_DIR", str(cache_dir))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    yield cache_dir


@pytest.fixture
def repo_payload() -> dict[str, Any]:
    return {
        "full_name": "encode/httpx",
        "description": "A next generation HTTP client for Python.",
        "stargazers_count": 13000,
        "forks_count": 800,
        "open_issues_count": 50,
        "language": "Python",
        "html_url": "https://github.com/encode/httpx",
        "pushed_at": "2026-01-02T03:04:05Z",
    }


def issue(n: int, *, pr: bool = False, login: str = "ada") -> dict[str, Any]:
    raw: dict[str, Any] = {
        "number": n,
        "title": f"issue {n}",
        "state": "open",
        "created_at": "2026-05-01T12:00:00Z",
        "html_url": f"https://github.com/o/r/issues/{n}",
        "user": {"login": login},
    }
    if pr:
        raw["pull_request"] = {"url": "..."}
    return raw


@dataclass
class FakeGitHub:
    """An httpx transport that answers from a function and records every request."""

    handler: Callable[[httpx.Request], httpx.Response]
    requests: list[httpx.Request] = field(default_factory=list)

    @property
    def transport(self) -> httpx.MockTransport:
        def record(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.handler(request)

        return httpx.MockTransport(record)


@pytest.fixture
def fake_github() -> Callable[[Callable[[httpx.Request], httpx.Response]], FakeGitHub]:
    return FakeGitHub
