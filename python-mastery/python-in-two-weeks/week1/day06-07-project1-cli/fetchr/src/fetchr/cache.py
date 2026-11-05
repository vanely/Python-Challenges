"""A tiny JSON file cache with TTL, plus a decorator that uses it."""

from __future__ import annotations

import functools
import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path.home() / ".cache" / "fetchr"


class Cache:
    def __init__(self, directory: Path = DEFAULT_DIR, ttl: float = 600) -> None:
        self.directory = directory
        self.ttl = ttl
        directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        return self.directory / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.ttl:
            path.unlink(missing_ok=True)
            return None
        return json.loads(path.read_text())

    def set(self, key: str, value: Any) -> None:
        self._path(key).write_text(json.dumps(value))

    def clear(self) -> int:
        files = list(self.directory.glob("*.json"))
        for f in files:
            f.unlink()
        return len(files)


def cached(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache a function's JSON-serialisable result keyed on its string args."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{fn.__qualname__}:{args!r}:{sorted(kwargs.items())!r}"
            hit = cache.get(key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper

    return decorator
