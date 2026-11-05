"""Implement these. See README.md for the spec and typecheck.py for the type contract."""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


def once(fn: Any) -> Any:
    raise NotImplementedError


def debounce(seconds: float) -> Any:
    raise NotImplementedError


def with_lock(lock: threading.Lock) -> Any:
    raise NotImplementedError


def inject_logger(fn: Any) -> Any:
    raise NotImplementedError


def ensure_async(fn: Any) -> Any:
    raise NotImplementedError


class count:
    def __init__(self, fn: Any) -> None:
        raise NotImplementedError


def validate_types(fn: Any) -> Any:
    raise NotImplementedError


class lazy:
    def __init__(self, fn: Callable[[Any], Any]) -> None:
        raise NotImplementedError
