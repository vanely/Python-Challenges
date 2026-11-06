# Step 2 — A file cache with TTL, and a caching decorator

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/test_fx_02_cache.py`

## What you'll have at the end

`cache.py` with:
- `Cache`: stores JSON values in files under a directory, expires them after `ttl` seconds, survives corrupt files, and never leaves a half-written file behind;
- `@cached(cache)`: a typed decorator that memoises any function with JSON-serialisable results.

GitHub's unauthenticated rate limit is 60 requests an hour. The cache is what makes `fetchr` usable without a token.

## Concepts

### `pathlib`: paths are objects

```python
from pathlib import Path
d = Path.home() / ".cache" / "fetchr"      # `/` joins; correct separator on every OS
d.mkdir(parents=True, exist_ok=True)      # mkdir -p
f = d / "abc.json"
f.write_text("...", encoding="utf-8"); f.read_text(encoding="utf-8")
f.stat().st_mtime                          # last-modified time, seconds since the epoch
f.unlink(missing_ok=True)                  # rm -f
list(d.glob("*.json"))
```

Pass `encoding="utf-8"` explicitly. Without it, Python 3.12 uses the platform's locale encoding, which on Windows is often `cp1252`, not UTF-8. PEP 686 makes UTF-8 the default in a later version; until you can rely on that, be explicit.

### Keys → filenames

Cache keys will be things like `/repos/encode/httpx?[('page', 1)]`, full of characters that are illegal in Windows filenames (`?`, `:`, `"`, `<`, `>`, `|`, `*`). Hash the key: `hashlib.sha256(key.encode()).hexdigest()` gives 64 hex characters that are safe everywhere, the same length for every key, and practically collision-free. Truncating to 24 characters (96 bits) is still collision-free for a local cache.

### TTL from the file's own mtime

There's no need to store a timestamp inside the file: the filesystem already records when it was last written. If `time.time() - path.stat().st_mtime > ttl`, the entry has expired. Delete it and report a miss.

### Atomic writes

`path.write_text(data)` opens the file, truncates it to zero bytes, and then writes. If the process dies in between (Ctrl-C, a crash, a full disk), or another `fetchr` process reads at that moment, the reader sees an empty or half-written file, and `json.loads` raises `JSONDecodeError` on the next run. **Forever**, until someone deletes the file.

The standard fix is to write to a temporary file in the same directory, then `os.replace(tmp, path)`. On POSIX, a rename within one filesystem is atomic: readers see either the old file or the new one, never a partial one. On Windows, `os.replace` uses `MoveFileEx` and gives the same never-partial result on NTFS. It can, however, raise `PermissionError` if another process has the target open at that instant. That's rare for a CLI cache, and the worst outcome is a failed `set`, never a corrupt file. Include the PID in the temp name so two processes don't share a temp file.

Even so, also treat a corrupt file as a miss. Files written by an older version of your code, or edited by hand, exist.

### EAFP: try it, don't check first

```python
# LBYL ("look before you leap"): race-prone
if path.exists():
    return path.read_text()          # the file can vanish between these two lines

# EAFP ("easier to ask forgiveness than permission"): idiomatic Python
try:
    return path.read_text()
except FileNotFoundError:
    return default
```

Another process (or `fetchr cache clear`) can delete the file between `exists()` and `read_text()`. With EAFP there's no gap. Python exceptions are cheap enough that this is the normal style, not a performance compromise.

### Sentinels: when `None` is a valid value

`cache.get(key)` returning `None` for a miss makes it impossible to cache `None`. JSON `null` is a perfectly good value, and a function that returns `None` would be called every single time. The fix is a **sentinel**, a private object nobody else can produce:

```python
_MISS = object()
hit = cache.get(key, _MISS)
if hit is not _MISS: ...
```

`is` compares identity, and no cached value can *be* that particular object. This is the pattern behind `dict.get(key, default)` and `next(it, default)`.

### Decorators with arguments are three functions deep

```python
@cached(cache)            # 1. cached(cache) runs first and returns `decorator`
def f(x): ...             # 2. decorator(f) runs at definition time and returns `wrapper`
f(1)                      # 3. wrapper(1) runs on every call
```

Day 4 covered the shape. Two things matter here:
- `@functools.wraps(fn)` copies `__name__`, `__doc__`, `__module__` and `__qualname__`, and sets `__wrapped__`. Without it, every decorated function shows up as `wrapper` in tracebacks, `--help` and logs.
- **Typing it.** `def cached[**P, R](cache: Cache) -> Callable[[Callable[P, R]], Callable[P, R]]` (PEP 695 syntax, 3.12) says "returns a decorator that preserves the exact signature". `**P` is a `ParamSpec`, a variable for the whole parameter list. mypy then checks calls to the decorated function exactly like calls to the original.

The cache returns `Any` (it's JSON), so returning a hit from a function declared to return `R` needs `cast(R, hit)`. `cast` does nothing at runtime; it's you telling the checker "trust me". Write it rarely and deliberately, and only where you know something the checker can't.

### Defaults are evaluated once, at definition time

```python
DEFAULT_DIR = Path.home() / ".cache" / "fetchr"
def __init__(self, directory: Path = DEFAULT_DIR): ...
```

`Path.home()` runs **at import**, so a test can't redirect it afterwards. And `def f(x=[])` shares one list across all calls, which is the most famous Python bug. Make the default `None` and compute the real value inside the function:

```python
def __init__(self, directory: Path | None = None, ttl: float = 600) -> None:
    self.directory = directory if directory is not None else default_dir()
```

`default_dir()` reads the `FETCHR_CACHE_DIR` environment variable **when called**, so tests (and users) can point the cache somewhere else.

## Build

### 1. `Cache`

```python
"""A tiny JSON file cache with TTL, plus a decorator that uses it."""

from __future__ import annotations

import functools
import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

_MISS = object()


def default_dir() -> Path:
    """Read at call time, not import time, so tests (and users) can redirect it."""
    override = os.environ.get("FETCHR_CACHE_DIR")
    return Path(override) if override else Path.home() / ".cache" / "fetchr"


class Cache:
    def __init__(self, directory: Path | None = None, ttl: float = 600) -> None:
        self.directory = directory if directory is not None else default_dir()
        self.ttl = ttl
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        return self.directory / f"{digest}.json"

    def get(self, key: str, default: Any = None) -> Any:
        path = self._path(key)
        try:
            if time.time() - path.stat().st_mtime > self.ttl:
                path.unlink(missing_ok=True)
                return default
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default
        except json.JSONDecodeError:  # truncated or corrupt: treat as a miss
            path.unlink(missing_ok=True)
            return default

    def clear(self) -> int:
        files = list(self.directory.glob("*.json"))
        for f in files:
            f.unlink(missing_ok=True)
        return len(files)
```

### 2. Your turn: `Cache.set`

`set(self, key: str, value: Any) -> None` writes `json.dumps(value)` to the key's path **atomically**: write a temp file in the same directory, then `os.replace` it onto the real path. After any number of `set` calls, the directory contains only `*.json` files, with no temp files left over.

<details><summary>Hint: the temp name</summary>

`path.with_suffix(f".{os.getpid()}.tmp")` keeps the temp file in the same directory, which is required for the rename to be atomic, and makes it unique per process. Its name doesn't end in `.json`, so `clear()` and `glob("*.json")` never see it.
</details>

### 3. Your turn: `@cached`

`cached(cache)` returns a decorator. The decorated function:
- builds a key from the function's identity and its arguments: `f"{fn.__module__}.{fn.__qualname__}:{args!r}:{sorted(kwargs.items())!r}"`. Different functions with the same arguments must not collide, which is why the qualified name is in the key;
- returns the cached value when there is one, **including a cached `None`**;
- otherwise calls the function, stores the result, and returns it;
- preserves `__name__` and `__doc__`, and sets `__wrapped__`;
- is fully typed with PEP 695 syntax, so `mypy --strict` passes.

<details><summary>Hint: the signature</summary>

```python
def cached[**P, R](cache: Cache) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ...
```
</details>

### 4. Play with it

```bash
uv run python
>>> from fetchr.cache import Cache, cached
>>> c = Cache(ttl=5)
>>> c.directory                      # where is it on your machine?
>>> @cached(c)
... def slow(n: int) -> int:
...     import time; time.sleep(1); return n * n
>>> slow(4)                          # ~1 s
>>> slow(4)                          # instant: served from the cache
>>> # wait 5 s and call again: slow again
>>> slow.__wrapped__(4)              # bypasses the cache
```

Open the cache directory and look at a file. It's just JSON.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_fx_02_cache.py
uv run mypy src && uv run ruff check .
```

## Pitfalls

- **`except Exception:` "just in case".** Catch the two failures you expect, `FileNotFoundError` and `JSONDecodeError`. A blanket `except` also hides a `PermissionError` that the user needs to see, and your own bugs (a `TypeError` in your code would become a silent permanent cache miss).
- **Caching a mutable result.** The cache returns a *new* object decoded from JSON on each hit, so callers can't corrupt it. An in-memory cache (`functools.lru_cache`) returns *the same* object every time. Mutate it once and every later caller sees the change.
- **Key stability.** `repr` of a `dict` argument depends on insertion order, and `repr` of an arbitrary object includes its memory address (`<Foo at 0x7f...>`), so it's never a hit. This decorator is for functions whose arguments are simple values. Say so in the docstring.
- **Clock skew in TTLs.** mtime is set by the filesystem, and `time.time()` by the OS clock. On a network drive they can disagree. That doesn't matter on a local disk, but it's a real bug in shared caches.

## Explain it back

1. Describe, step by step, how a non-atomic `write_text` leaves a cache permanently broken. What exactly does the next run see?
2. Why must the temp file be in the same directory as the target for `os.replace` to be atomic?
3. Why is `if path.exists(): path.read_text()` wrong even in a single-user CLI?
4. Why does `cache.get(key) is None` break caching of functions that return `None`? Why can't any value from JSON ever be `_MISS`?
5. What do `__wrapped__` and `__qualname__` give you? Find one place in the standard library that uses `__wrapped__` (hint: `inspect.signature`).
6. What's wrong with `def __init__(self, directory: Path = Path.home() / ".cache")` for testing? What's the general rule?
