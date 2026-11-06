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

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(value), encoding="utf-8")
        os.replace(tmp, path)  # atomic: readers see the old file or the new one, never half

    def clear(self) -> int:
        files = list(self.directory.glob("*.json"))
        for f in files:
            f.unlink(missing_ok=True)
        return len(files)


def cached[**P, R](cache: Cache) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Cache a function's JSON-serialisable result, keyed on its arguments' reprs."""

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = f"{fn.__module__}.{fn.__qualname__}:{args!r}:{sorted(kwargs.items())!r}"
            hit = cache.get(key, _MISS)
            if hit is not _MISS:
                return cast(R, hit)
            result = fn(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper

    return decorator
