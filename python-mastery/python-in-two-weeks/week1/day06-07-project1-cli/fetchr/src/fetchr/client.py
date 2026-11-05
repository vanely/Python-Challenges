"""GitHub API client. A context manager over httpx.Client, with lazy pagination."""

from __future__ import annotations

import os
from collections.abc import Iterator
from types import TracebackType
from typing import Any, cast

import httpx

from fetchr.cache import Cache
from fetchr.models import Issue, IssuePayload, IssueState, Repo, RepoPayload

API = "https://api.github.com"


class GitHubClient:
    def __init__(self, cache: Cache | None = None, token: str | None = None) -> None:
        token = token or os.environ.get("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "fetchr"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(base_url=API, headers=headers, timeout=15)
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
        if self._cache and (hit := self._cache.get(key)) is not None:
            return hit
        resp = self._http.get(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        if self._cache:
            self._cache.set(key, data)
        return data

    # --- public ------------------------------------------------------------------
    def repo(self, owner: str, name: str) -> Repo:
        return Repo.from_api(cast(RepoPayload, self._get(f"/repos/{owner}/{name}")))

    def issues(
        self, owner: str, name: str, state: IssueState = "open", limit: int | None = None
    ) -> Iterator[Issue]:
        """Lazily paginate. Stops at `limit` or when a page comes back empty."""
        yielded = 0
        page = 1
        while True:
            batch = cast(
                list[IssuePayload],
                self._get(f"/repos/{owner}/{name}/issues", state=state, per_page=100, page=page),
            )
            if not batch:
                return
            for raw in batch:
                if "pull_request" in raw:  # GitHub returns PRs in /issues; skip them
                    continue
                yield Issue.from_api(raw)
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
            page += 1
