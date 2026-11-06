"""Type contract. Run: mypy --strict --disable-error-code=empty-body decorators.py typecheck.py
Expected output: only the eleven `note: Revealed type` lines, matching the comments, then Success.
(Comments use current mypy's short names; older 1.x releases print `builtins.int`, `Union[...]`.)"""
from __future__ import annotations

import logging
import threading
from collections.abc import Coroutine
from typing import Any

from decorators import count, debounce, ensure_async, inject_logger, lazy, once, validate_types, with_lock


@once
def load(path: str) -> dict[str, int]: ...


@debounce(0.5)
def save(data: bytes) -> int: ...


@with_lock(threading.Lock())
def tick(n: int) -> None: ...


@inject_logger
def work(logger: logging.Logger, n: int) -> str: ...


@ensure_async
def sync_fn(x: int) -> str: ...


@ensure_async
async def async_fn(x: int) -> str: ...


@count
def counted(x: int, y: str = "") -> float: ...


@validate_types
def typed(a: int, b: str) -> bool: ...


class C:
    @lazy
    def value(self) -> list[int]: ...


reveal_type(load)        # N: Revealed type is "def (path: str) -> dict[str, int]"
reveal_type(save)        # N: Revealed type is "def (data: bytes) -> int | None"
reveal_type(tick)        # N: Revealed type is "def (n: int)"
reveal_type(work)        # N: Revealed type is "def (n: int) -> str"
reveal_type(sync_fn)     # N: Revealed type is "def (x: int) -> typing.Coroutine[Any, Any, str]"
reveal_type(async_fn)    # N: Revealed type is "def (x: int) -> typing.Coroutine[Any, Any, str]"
reveal_type(counted.calls)   # N: Revealed type is "int"
reveal_type(counted(1))      # N: Revealed type is "float"
reveal_type(typed)       # N: Revealed type is "def (a: int, b: str) -> bool"
reveal_type(C().value)   # N: Revealed type is "list[int]"
reveal_type(C.value)     # N: Revealed type is "decorators.lazy[list[int]]"

# These MUST be errors once your types are right (unused-ignore fires otherwise):
load(1)                  # type: ignore[arg-type]
work(logging.getLogger(), 1)  # type: ignore[arg-type,call-arg]
counted("x")             # type: ignore[arg-type]
_c: Coroutine[Any, Any, str] = sync_fn(1)
