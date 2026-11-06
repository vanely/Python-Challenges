import asyncio
import logging
import threading
import time

import pytest

from decorators import count, debounce, ensure_async, inject_logger, lazy, once, validate_types, with_lock


def test_once() -> None:
    calls = []

    @once
    def f(x: int) -> int:
        calls.append(x)
        return x * 2

    assert f(1) == 2 and f(2) == 2 and calls == [1]


def test_debounce() -> None:
    @debounce(0.05)
    def f(x: int) -> int:
        return x

    assert f(1) == 1
    assert f(2) is None
    time.sleep(0.15)
    assert f(3) == 3


def test_with_lock() -> None:
    lock = threading.Lock()

    @with_lock(lock)
    def f() -> bool:
        return lock.locked()

    assert f() is True and not lock.locked()


def test_inject_logger(caplog: pytest.LogCaptureFixture) -> None:
    @inject_logger
    def f(logger: logging.Logger, n: int) -> str:
        logger.warning("n=%d", n)
        return logger.name

    with caplog.at_level(logging.WARNING):
        name = f(3)
    assert "n=3" in caplog.text and name == "test_decorators"   # logger named after the module


def test_ensure_async() -> None:
    @ensure_async
    def s(x: int) -> int:
        return x + 1

    @ensure_async
    async def a(x: int) -> int:
        return x + 2

    assert asyncio.run(s(1)) == 2 and asyncio.run(a(1)) == 3


def test_count() -> None:
    @count
    def f(x: int) -> int:
        return x

    f(1); f(2)
    assert f.calls == 2 and f.__name__ == "f"


def test_validate_types() -> None:
    @validate_types
    def f(a: int, b: str = "x") -> bool:
        return True

    assert f(1) and f(1, b="y")
    with pytest.raises(TypeError, match="b"):
        f(1, b=2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="a"):
        f("no")  # type: ignore[arg-type]


def test_lazy() -> None:
    n = 0

    class C:
        @lazy
        def v(self) -> int:
            nonlocal n
            n += 1
            return 42

    c = C()
    assert c.v == 42 and c.v == 42 and n == 1
    assert isinstance(C.v, lazy)
