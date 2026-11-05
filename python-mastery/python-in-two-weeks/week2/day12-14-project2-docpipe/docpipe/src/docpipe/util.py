"""Small cross-cutting helpers: timing decorator, retry, hashing."""

from __future__ import annotations

import functools
import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
log = logging.getLogger(__name__)


def timed[**Q, S](fn: Callable[Q, S]) -> Callable[Q, S]:
    @functools.wraps(fn)
    def wrapper(*args: Q.args, **kwargs: Q.kwargs) -> S:
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            log.debug("%s took %.3fs", fn.__qualname__, time.perf_counter() - t0)

    return wrapper


def retry(
    times: int = 3, exceptions: tuple[type[Exception], ...] = (OSError,), delay: float = 0.2
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last = e
                    log.warning("%s attempt %d/%d failed: %s", fn.__name__, attempt, times, e)
                    time.sleep(delay)
            assert last is not None
            raise last

        return wrapper

    return decorator


def sha256_of(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
