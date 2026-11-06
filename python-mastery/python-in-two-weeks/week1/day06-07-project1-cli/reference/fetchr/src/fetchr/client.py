"""GitHub API client. A context manager over httpx.Client, with lazy pagination."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, cast

import httpx

from fetchr.cache import Cache
from fetchr.models import Issue, IssuePayload, IssueState, Repo, RepoPayload

API = "https://api.github.com"
PER_PAGE = 100
_MISS = object()


class RateLimitError(Exception):
    def __init__(self, reset_at: datetime | None) -> None:
        when = reset_at.isoformat() if reset_at else "unknown"
        super().__init__(f"GitHub rate limit exceeded; resets at {when}")
        self.reset_at = reset_at


class GitHubClient:
    def __init__(
        self,
        cache: Cache | None = None,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        token = token or os.environ.get("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "fetchr"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(base_url=API, headers=headers, timeout=15, transport=transport)
        self._cache = cache

    # --- context manager -------------------------------------------------------
    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._http.close()

    # --- low level -------------------------------------------------------------
    def _get(self, path: str, **params: Any) -> Any:
        key = f"{path}?{sorted(params.items())!r}"
        if self._cache is not None:
            hit = self._cache.get(key, _MISS)
            if hit is not _MISS:
                return hit
        resp = self._http.get(path, params=params)
        _raise_for_rate_limit(resp)
        resp.raise_for_status()
        data = resp.json()
        if self._cache is not None:
            self._cache.set(key, data)
        return data

    # --- public ------------------------------------------------------------------
    def repo(self, owner: str, name: str) -> Repo:
        return Repo.from_api(cast(RepoPayload, self._get(f"/repos/{owner}/{name}")))

    def issues(
        self,
        owner: str,
        name: str,
        state: IssueState = IssueState.OPEN,
        limit: int | None = None,
    ) -> Iterator[Issue]:
        """Lazily paginate. Stops at `limit`, or after the first short page."""
        yielded = 0
        page = 1
        while True:
            batch = cast(
                list[IssuePayload],
                self._get(
                    f"/repos/{owner}/{name}/issues",
                    state=str(state),
                    per_page=PER_PAGE,
                    page=page,
                ),
            )
            for raw in batch:
                if "pull_request" in raw:  # GitHub returns PRs in /issues; skip them
                    continue
                yield Issue.from_api(raw)
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
            if len(batch) < PER_PAGE:  # a short (or empty) page is the last one
                return
            page += 1


def _raise_for_rate_limit(resp: httpx.Response) -> None:
    if resp.status_code in (403, 429) and resp.headers.get("x-ratelimit-remaining") == "0":
        reset = resp.headers.get("x-ratelimit-reset")
        reset_at = datetime.fromtimestamp(int(reset), tz=UTC) if reset else None
        raise RateLimitError(reset_at)
