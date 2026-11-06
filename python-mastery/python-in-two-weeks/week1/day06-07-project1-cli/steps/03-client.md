# Step 3 — The GitHub client: a context manager with lazy pagination

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/test_fx_03_client.py`

## What you'll have at the end

`client.py` with a `GitHubClient` that:
- owns one HTTP connection pool and closes it reliably (`with GitHubClient() as gh:`);
- can be tested without the network, because it accepts an httpx **transport**;
- caches successful responses;
- yields issues **lazily**, fetching page 2 only if you keep iterating past page 1.

## Concepts

### `httpx.Client`, not `httpx.get`

`httpx.get(url)` opens a TCP+TLS connection, makes one request, and closes it. A `Client` keeps a **connection pool**, so ten requests to `api.github.com` reuse one TLS connection, and the TLS handshake usually costs more than the request itself. It also holds shared configuration: `base_url`, default headers, and `timeout`. Always set a timeout: without one, a hung server hangs your CLI forever. (httpx defaults to 5 s; we use 15 s.)

### The context-manager protocol

```python
with GitHubClient() as gh:      # calls gh.__enter__(); `as` binds its return value
    gh.repo("a", "b")
# gh.__exit__(exc_type, exc, tb) runs here, whether the block returned or raised
```

It's `try/finally` packaged into the object. TypeScript 5.2 added the same idea as `using` with `[Symbol.dispose]`. `__exit__` receives the in-flight exception, if any. Returning a truthy value from it **swallows** that exception, which you almost never want, so ours returns `None`.

### A seam for tests: inject the transport

httpx splits the client (cookies, headers, redirects, timeouts) from the **transport** (actually sending bytes). `httpx.MockTransport(handler)` is a transport that calls your function instead of the network:

```python
def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/repos/o/r"
    return httpx.Response(200, json={"full_name": "o/r"})

client = httpx.Client(transport=httpx.MockTransport(handler))
```

So `GitHubClient(transport=...)` passes it straight through to `httpx.Client`. In production it's `None`, and httpx uses its real transport. This is **dependency injection without a framework**: a constructor parameter with a production default.

Compare it with monkeypatching `httpx.Client.get`. That couples your tests to *which method you call*: switch to `self._http.request("GET", ...)` and every test breaks, even though the behaviour is identical. A transport sees every request, however it was made.

### `raise_for_status()`

httpx doesn't raise on 4xx/5xx; `resp.status_code` is just a number. `resp.raise_for_status()` raises `httpx.HTTPStatusError` (which has `.request` and `.response`) for 4xx/5xx. Call it **before** caching, so you never cache an error page.

### Generators: functions that pause

```python
def count_up() -> Iterator[int]:
    print("started")
    n = 0
    while True:
        yield n
        n += 1

it = count_up()     # nothing printed: calling a generator function only creates the generator
next(it)            # prints "started", returns 0, pauses at `yield`
next(it)            # resumes after `yield`, returns 1
```

A TS `function*` works the same way. For pagination, this means **the caller decides how much to fetch**. `list(gh.issues(...))` fetches every page. `next(gh.issues(...))` fetches only page 1. A `limit` inside the generator stops the loop, and `return` inside a generator ends the iteration (it raises `StopIteration` for you).

### GitHub pagination

`GET /repos/{owner}/{repo}/issues?state=open&per_page=100&page=N`
- `per_page` maxes out at 100.
- Pages past the end return `[]`.
- GitHub's "issues" endpoint **also returns pull requests**, marked with a `pull_request` key. Skip those.
- When to stop: either follow the `Link: <...>; rel="next"` header, or stop when a page comes back **shorter than `per_page`**, since a short page must be the last one. The short-page rule saves the extra request for the empty page. Its one edge case: if the last page is *exactly* full, you need one more request to see the empty page.

Note that a page with 100 items where 30 are PRs is still a **full** page. Decide "was this the last page?" from the raw batch length, not from how many issues you yielded.

### `cast` at the JSON boundary

`resp.json()` returns `Any`. `cast(RepoPayload, data)` tells mypy to treat it as a `RepoPayload` from here on. It's a promise, not a check. That's the honest situation with JSON from an API you don't control: the TypedDict documents the shape you rely on, and `from_api` deals with missing keys.

## Build

### 1. The client, minus `issues`

```python
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
PER_PAGE = 100
_MISS = object()


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

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._http.close()

    def _get(self, path: str, **params: Any) -> Any:
        key = f"{path}?{sorted(params.items())!r}"
        if self._cache is not None:
            hit = self._cache.get(key, _MISS)
            if hit is not _MISS:
                return hit
        resp = self._http.get(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        if self._cache is not None:
            self._cache.set(key, data)
        return data

    def repo(self, owner: str, name: str) -> Repo:
        return Repo.from_api(cast(RepoPayload, self._get(f"/repos/{owner}/{name}")))
```

Notes:
- GitHub **requires** a `User-Agent` header and rejects requests without one.
- `sorted(params.items())` makes the key independent of keyword order: `_get(p, a=1, b=2)` and `_get(p, b=2, a=1)` are the same request.
- `if self._cache is not None` rather than `if self._cache`. Any object with a `__len__` that returns 0 is falsy, so get into the habit of testing for `None` explicitly.

### 2. Your turn: `issues`

```python
def issues(
    self,
    owner: str,
    name: str,
    state: IssueState = IssueState.OPEN,
    limit: int | None = None,
) -> Iterator[Issue]:
```

A generator that:
- requests `/repos/{owner}/{name}/issues` with `state`, `per_page=PER_PAGE` and `page` (starting at 1), through `self._get`;
- skips entries that have a `pull_request` key, and yields `Issue.from_api(raw)` for the rest;
- stops as soon as it has yielded `limit` issues, without requesting another page;
- stops after the first page whose raw length is `< PER_PAGE`;
- makes **no** request until the caller asks for the first item.

The checkpoint counts requests: two pages (100 + 2 items) is exactly 2 requests, an empty repo is 1, and one exactly-full page is 2.

<details><summary>Hint: the shape</summary>

`yielded = 0; page = 1; while True:` fetch a batch; loop over it with the PR skip, yield, and the limit check; after the inner loop, `if len(batch) < PER_PAGE: return`; then `page += 1`.
</details>

<details><summary>Hint: state in params</summary>

`state=str(state)` sends `"open"`. A `StrEnum` member formats as its value, so `str(IssueState.OPEN) == "open"`. With a plain `Enum` you'd get `"IssueState.OPEN"` and GitHub would reject it.
</details>

### 3. Try it for real (needs network)

```bash
uv run python
>>> from fetchr.client import GitHubClient
>>> with GitHubClient() as gh:
...     print(gh.repo("encode", "httpx"))
...     it = gh.issues("encode", "httpx", limit=3)
...     print([i.title for i in it])
```

Then `from fetchr.cache import Cache`, make the same calls with `GitHubClient(cache=Cache())` twice, and time them.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_fx_03_client.py
uv run mypy src && uv run ruff check .
```

## Your own tests

Write `tests/test_client.py` with at least two tests that use `httpx.MockTransport`: one for pagination and one for an HTTP error. Write `tests/test_models.py` and `tests/test_cache.py` too, if you haven't. The checkpoints check that your code works. Your own tests are where you practise writing tests, which you'll do for the rest of your career.

## Pitfalls

- **Returning a list "for simplicity".** `return [Issue.from_api(r) for r in all_pages]` fetches every page of a 5,000-issue repo to show the first 20. That's the TS habit of `async function getAll(): Promise<Issue[]>`.
- **Counting yielded issues to decide the last page.** That breaks when a full page contains PRs.
- **Using the client after `with`.** httpx raises `RuntimeError` on a closed client. That's also why the CLI must consume the generator *inside* the `with` block: `list(gh.issues(...))` must run before `__exit__` closes the pool.
- **Swallowing in `__exit__`.** `return True` from `__exit__` makes every exception in the block vanish.

## Explain it back

1. Calling `gh.issues("o", "r")` makes no request. What object do you get back, and when does the first request happen?
2. Why does the PR filter not change the "last page" decision? Construct the bug you'd get if it did.
3. Why is injecting a transport a better seam than monkeypatching `httpx.Client.get`? What refactor breaks the monkeypatch but not the transport?
4. What would happen if `_get` cached before calling `raise_for_status()`?
5. Why does `list(gh.issues(...))` have to run inside the `with` block?
