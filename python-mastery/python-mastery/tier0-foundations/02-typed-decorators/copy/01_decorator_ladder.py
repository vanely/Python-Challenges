"""0.2 — The decorator typing ladder. mypy --strict must pass. `reveal_type` lines are for
`mypy` output only; they're no-ops at runtime because of the TYPE_CHECKING guard."""
from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, Concatenate, Generic, ParamSpec, TypeVar, overload

P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


# --- 1. Passthrough: returns the same function object -------------------------------------------
_registry: dict[str, Callable[..., Any]] = {}


def register(fn: F) -> F:
    _registry[fn.__name__] = fn
    return fn


@register
def handler(x: int) -> str:
    return str(x)


# --- 2. Wrapper, same signature (the 90% case) --------------------------------------------------------
def timed(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            print(f"  {fn.__name__}: {(time.perf_counter() - t0) * 1e3:.2f}ms")

    return wrapper


@timed
def add(a: int, b: int = 0) -> int:
    return a + b


# --- 3. Wrapper that changes the return type -------------------------------------------------------------
def to_async(fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Run a sync function in a thread; the decorated function is now a coroutine function.
    (Coroutine, not Awaitable: asyncio.run() demands a real coroutine.)"""

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(fn, *args, **kwargs)

    return wrapper


def swallow(fn: Callable[P, R]) -> Callable[P, R | None]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None

    return wrapper


@to_async
def slow_square(n: int) -> int:
    return n * n


@swallow
def parse(s: str) -> int:
    return int(s)


# --- 4. Concatenate: inject or strip a leading argument ---------------------------------------------------
class Request:
    def __init__(self, user: str) -> None:
        self.user = user


def with_request(fn: Callable[Concatenate[Request, P], R]) -> Callable[P, R]:
    """Decorated function no longer takes `request`; the wrapper supplies it."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(Request("ada"), *args, **kwargs)

    return wrapper


@with_request
def greet(request: Request, greeting: str = "hi") -> str:
    return f"{greeting} {request.user}"


# --- 5. Parameterised decorator: a function that returns a decorator ---------------------------------------
def retry(times: int, exceptions: tuple[type[Exception], ...] = (Exception,)) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    if attempt == times - 1:
                        raise
            raise AssertionError("unreachable")

        return wrapper

    return decorator


# Decorator usable both bare and with args: overloads on the factory.
@overload
def logged(fn: Callable[P, R]) -> Callable[P, R]: ...
@overload
def logged(*, prefix: str) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
def logged(fn: Callable[P, R] | None = None, *, prefix: str = "") -> Any:
    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            print(f"  {prefix}{f.__name__}")
            return f(*args, **kwargs)

        return wrapper

    return decorator if fn is None else decorator(fn)


@logged
def a1() -> int:
    return 1


@logged(prefix=">> ")
def a2() -> int:
    return 2


# --- 6. Class-based decorator, generic in P and R -------------------------------------------------------------
class CountCalls(Generic[P, R]):
    def __init__(self, fn: Callable[P, R]) -> None:
        functools.update_wrapper(self, fn)
        self.fn = fn
        self.calls = 0

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        self.calls += 1
        return self.fn(*args, **kwargs)


@CountCalls
def ping(x: int) -> int:
    return x


# --- 7. Method decorators: P already carries `self` ----------------------------------------------------------
class Service:
    @timed
    def work(self, n: int) -> int:
        return n * 2

    @retry(times=2)
    def flaky(self) -> str:
        return "ok"


# --- 8. Decorator returning a descriptor (cached_property, typed) ---------------------------------------------
T_co = TypeVar("T_co", covariant=True)


class cached(Generic[T_co]):
    def __init__(self, fn: Callable[[Any], T_co]) -> None:
        self.fn = fn
        self.name = fn.__name__

    @overload
    def __get__(self, obj: None, owner: type) -> cached[T_co]: ...
    @overload
    def __get__(self, obj: object, owner: type) -> T_co: ...
    def __get__(self, obj: object | None, owner: type) -> cached[T_co] | T_co:
        if obj is None:
            return self
        value = self.fn(obj)
        obj.__dict__[self.name] = value
        return value


class Config:
    @cached
    def settings(self) -> dict[str, int]:
        print("  loading settings")
        return {"a": 1}


# --- checks --------------------------------------------------------------------------------------------------
if TYPE_CHECKING:
    reveal_type(add)              # def (a: int, b: int = ...) -> int
    reveal_type(slow_square)      # def (n: int) -> Coroutine[Any, Any, int]
    reveal_type(parse)            # def (s: str) -> int | None
    reveal_type(greet)            # def (greeting: str = ...) -> str   (no request!)
    reveal_type(a2)               # def () -> int
    reveal_type(ping)             # CountCalls[[x: int], int]
    reveal_type(Config().settings)  # dict[str, int]
    reveal_type(Config.settings)    # cached[dict[str, int]]

if __name__ == "__main__":
    print(add(1, 2), parse("x"), greet("hello"), a1(), a2(), ping(1), ping.calls)
    print(asyncio.run(slow_square(4)))
    print(Service().work(3), Service().flaky())
    c = Config()
    print(c.settings, c.settings)
    # add("x")            # mypy: Argument 1 to "add" has incompatible type "str"
    # greet(Request("x")) # mypy: Argument 1 has incompatible type "Request"; expected "str"
