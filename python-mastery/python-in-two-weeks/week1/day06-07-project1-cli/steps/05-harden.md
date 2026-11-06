# Step 5 — Failure modes: one clean line, exit code 1, never a traceback

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/test_fx_05_errors.py`

## What you'll have at the end

- A typed `RateLimitError` that tells the user when they can try again.
- A single place in the CLI that turns *expected* failures (404, 5xx, network down, timeout, rate limit) into one readable line on stderr and exit code 1.
- Your own test suite, plus ruff and `mypy --strict`, all green.
- A diff against the reference, written up in `NOTES.md`.

## Concepts

### Three kinds of failure

| Kind | Example | What the user should see |
|---|---|---|
| Usage error | `fetchr repo nope` | Usage line + message, exit 2 (step 4) |
| Expected runtime failure | 404, timeout, no network, rate limit | One line on stderr saying what happened and what to do, exit 1 |
| Bug | `KeyError` in your code | A traceback. **Don't catch these.** |

The third row matters. Wrapping `main()` in `except Exception: print("something went wrong")` turns your bugs into unanswerable bug reports. Catch exactly the exceptions you can explain to the user.

### httpx's exception tree

```
httpx.HTTPError
├── httpx.RequestError          # no usable response: the request itself failed
│   ├── httpx.TransportError
│   │   ├── httpx.TimeoutException  (ConnectTimeout, ReadTimeout, …)
│   │   ├── httpx.NetworkError      (ConnectError, ReadError, …)
│   │   └── …
│   └── …
└── httpx.HTTPStatusError       # got a response, and it was 4xx/5xx (raise_for_status)
```

Catching `httpx.RequestError` covers "no network", DNS failures and timeouts in one clause. `HTTPStatusError` carries `.response.status_code`. Both carry `.request.url`.

### GitHub rate limiting

Unauthenticated: 60 requests/hour per IP. With a token: 5,000/hour. When you run out, GitHub answers **403** (sometimes **429**) with these headers:

```
x-ratelimit-remaining: 0
x-ratelimit-reset: 1800000000       # Unix epoch seconds when the window resets
```

A 403 **without** `remaining: 0` is a real permission error (a private repo, a blocked token) and must stay an ordinary HTTP error. So check the header, not just the status code.

### Custom exceptions carry data

```python
class RateLimitError(Exception):
    def __init__(self, reset_at: datetime | None) -> None:
        when = reset_at.isoformat() if reset_at else "unknown"
        super().__init__(f"GitHub rate limit exceeded; resets at {when}")
        self.reset_at = reset_at
```

A message string is for humans. An attribute is for code: a retrying caller could `sleep` until `e.reset_at`. Always call `super().__init__(message)` so `str(e)` and tracebacks show the message.

`datetime.fromtimestamp(epoch, tz=UTC)` gives an aware datetime. Without `tz=` it returns *local naive* time, the Step 1 bug again.

### `NoReturn`, and context managers as error boundaries

```python
def _fail(message: str) -> NoReturn:
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(code=1)
```

`NoReturn` tells mypy this function never returns normally. Code after a `_fail(...)` call is unreachable, so mypy won't complain that a variable "might be unbound" on that path. Annotate it `-> None` instead and you get exactly the wrong signal.

`typer.Exit(code=1)` is how you leave a typer command with a specific exit code and no traceback. It's an exception that the CLI's top level converts into `sys.exit(1)`. Note that it subclasses `RuntimeError`, so a stray `except Exception:` between `_fail` and the top level would swallow it. That's one more reason not to write those.

To avoid repeating the same `try/except` in every command, write the error mapping **once** as a context manager:

```python
@contextmanager
def _github_errors() -> Iterator[None]:
    try:
        yield               # the body of the `with` block runs here
    except httpx.HTTPStatusError as e:
        _fail(f"HTTP {e.response.status_code} for {e.request.url}")
```

`@contextlib.contextmanager` turns a generator into a context manager: code before `yield` is `__enter__`, and an exception raised in the `with` body is **re-raised at the `yield`**, so a `try` around the `yield` catches it. Commands then read:

```python
with _github_errors(), _client() as gh:
    found = [gh.repo(owner, name) for owner, name in pairs]
```

Order matters: `_github_errors()` is entered first and exited last, so it also catches errors from `_client()`'s `__exit__`.

## Build

### 1. `_fail` and the error boundary

In `cli.py`, add `err_console` to the imports from `render`, plus `NoReturn`, `Iterator`, `contextmanager` and `httpx`. Add `_fail` and the `_github_errors` above, then wrap the `with` in `repos` and `issues`:

```python
with _github_errors(), _client() as gh:
```

Run `uv run fetchr repo encode/does-not-exist-xyz; echo "exit: $?"`. You should see one red line and `exit: 1`.

### 2. Your turn: the rate limit

In `client.py`:
- define `RateLimitError` as above;
- write `_raise_for_rate_limit(resp: httpx.Response) -> None`: if the status is 403 or 429 **and** `x-ratelimit-remaining` is `"0"`, raise `RateLimitError` with `reset_at` parsed from `x-ratelimit-reset` (aware, UTC), or `None` if that header is missing;
- call it in `_get` **before** `raise_for_status()`.

httpx headers are case-insensitive: `resp.headers.get("x-ratelimit-remaining")` matches `X-RateLimit-Remaining`.

### 3. Your turn: the remaining branches

Extend `_github_errors` so that:
- `RateLimitError` produces a message containing the reset time and telling the user to set `GITHUB_TOKEN`;
- `httpx.RequestError` (connect failures, timeouts) produces a message containing the word "network" and the URL.

Branch order matters: `except` clauses are tried top to bottom, and the first match wins. `RateLimitError` isn't an httpx exception, so its position doesn't matter. But think about what would happen if you caught `httpx.HTTPError` first.

### 4. Your own tests, and the gates

Finish `tests/`:
- `test_models.py`: the null/missing cases from step 1;
- `test_cache.py`: roundtrip, TTL (use `os.utime` to age a file instead of `sleep`), the cached-`None` case;
- `test_client.py`: pagination and an error, with `httpx.MockTransport`;
- `test_cli.py`: one success and one failure through `typer.testing.CliRunner`. Check `result.exit_code` and `result.stdout`/`result.stderr`.

Then the course rule from the Stage 1 README:

```bash
uv run pytest                              # your tests
uv run pytest ../checkpoints               # all 5 checkpoints
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
```

### 5. Diff against the reference

Now open `../reference/fetchr/`. For every file, note in `NOTES.md` what differs and which version is better and why. Common findings are worth writing down even when yours is fine: different names, a different stop condition, or a `try` placed at a different level.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_fx_05_errors.py
```

## Pitfalls

- **`except Exception` in `_github_errors`.** Your `KeyError` bugs now print "error: 'stargazers_count'" and exit 1. Nobody can debug that.
- **Printing errors to stdout.** `fetchr repos ... --json | jq` then fails with a JSON parse error instead of showing your message.
- **`raise typer.Exit(1)` deep inside `client.py`.** The client is a library. It raises domain exceptions (`RateLimitError`, `HTTPStatusError`), and only the CLI decides that they mean "print and exit". A future web UI could use the same client.
- **Naive reset time.** `datetime.fromtimestamp(reset)` without `tz=` silently gives local time.

## Explain it back

1. Which failures should end in a traceback, and why is that a feature?
2. Why does `_raise_for_rate_limit` run before `raise_for_status()`? What would the user see if the order were reversed?
3. In `@contextmanager`, where does an exception from the `with` body "appear" inside your generator?
4. What does `NoReturn` change for mypy? Write a three-line example where `-> None` causes a false "possibly unbound" or "missing return" error.
5. Why must the client never call `typer.Exit`?
6. List three differences between your code and the reference, and say which version you'd keep for each.
