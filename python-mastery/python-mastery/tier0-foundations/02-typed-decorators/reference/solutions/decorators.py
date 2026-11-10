"""Reference solutions. mypy --strict clean; passes typecheck.py and test_decorators.py."""
from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import threading
import time
from collections.abc import Callable, Coroutine
from typing import Any, Concatenate, Generic, ParamSpec, TypeVar, get_type_hints, overload

P = ParamSpec("P")
R = TypeVar("R")
T_co = TypeVar("T_co", covariant=True)
_UNSET = object()


def once(fn: Callable[P, R]) -> Callable[P, R]:
    result: Any = _UNSET

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        nonlocal result
        if result is _UNSET:
            result = fn(*args, **kwargs)
        return result  # type: ignore[no-any-return]

    return wrapper


def debounce(seconds: float) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R | None]:
        last = -float("inf")

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            nonlocal last
            now = time.perf_counter()
            if now - last < seconds:
                return None
            last = now
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def with_lock(lock: threading.Lock) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with lock:
                return fn(*args, **kwargs)

        return wrapper

    return decorator


def inject_logger(fn: Callable[Concatenate[logging.Logger, P], R]) -> Callable[P, R]:
    logger = logging.getLogger(fn.__module__)

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(logger, *args, **kwargs)

    return wrapper


@overload
def ensure_async(fn: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]: ...
@overload
def ensure_async(fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]: ...
def ensure_async(fn: Callable[P, Any]) -> Callable[P, Coroutine[Any, Any, Any]]:
    if inspect.iscoroutinefunction(fn):
        return fn

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        return await asyncio.to_thread(fn, *args, **kwargs)

    return wrapper


class count(Generic[P, R]):
    def __init__(self, fn: Callable[P, R]) -> None:
        functools.update_wrapper(self, fn)
        self._fn = fn
        self.calls = 0

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        self.calls += 1
        return self._fn(*args, **kwargs)


def validate_types(fn: Callable[P, R]) -> Callable[P, R]:
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        for name, value in bound.arguments.items():
            expected = hints.get(name)
            if isinstance(expected, type) and not isinstance(value, expected):
                raise TypeError(f"{name}: expected {expected.__name__}, got {type(value).__name__}")
        return fn(*args, **kwargs)

    return wrapper


class lazy(Generic[T_co]):
    def __init__(self, fn: Callable[[Any], T_co]) -> None:
        self.fn = fn
        self.name = fn.__name__

    @overload
    def __get__(self, obj: None, owner: type) -> lazy[T_co]: ...
    @overload
    def __get__(self, obj: object, owner: type) -> T_co: ...
    def __get__(self, obj: object | None, owner: type) -> lazy[T_co] | T_co:
        if obj is None:
            return self
        value = self.fn(obj)
        obj.__dict__[self.name] = value
        return value
