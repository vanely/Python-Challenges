import threading

import pytest

from lru import lru


def test_basic_and_info() -> None:
    calls = []

    @lru(maxsize=2)
    def f(x: int) -> int:
        calls.append(x)
        return x * 2

    assert f(1) == 2 and f(1) == 2 and f(2) == 4
    assert f.cache_info().hits == 1 and f.cache_info().misses == 2
    f(3)                                   # evicts 1 (least recently used)
    f(1)                                   # miss again
    assert calls == [1, 2, 3, 1]
    assert f.cache_info().currsize == 2
    f.cache_clear()
    assert f.cache_info().currsize == 0 and f.cache_info().hits == 0


def test_lru_order_refresh_on_hit() -> None:
    @lru(maxsize=2)
    def f(x: int) -> int:
        return x

    f(1); f(2); f(1); f(3)                 # 1 refreshed, so 2 is evicted
    f(1)
    assert f.cache_info().hits == 2


def test_typed_and_kwargs() -> None:
    @lru(typed=True)
    def f(x: object, *, y: int = 0) -> str:
        return f"{x!r}-{y}"

    f(1); f(1.0)
    assert f.cache_info().misses == 2      # typed: int vs float differ
    f(1, y=0); f(1, y=0)
    assert f.cache_info().hits == 1


def test_unhashable_raises_and_does_not_poison() -> None:
    @lru
    def f(x: object) -> object:
        return x

    with pytest.raises(TypeError):
        f([1])
    assert f.cache_info().currsize == 0


def test_exception_not_cached() -> None:
    n = 0

    @lru
    def f() -> None:
        nonlocal n
        n += 1
        raise ValueError

    for _ in range(2):
        with pytest.raises(ValueError):
            f()
    assert n == 2 and f.cache_info().currsize == 0


def test_unbounded_recursion() -> None:
    @lru(maxsize=None)
    def fib(n: int) -> int:
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    assert fib(300) == 222232244629420445529739893461909967206666939096499764990979600
    assert fib.cache_info().currsize == 301


def test_threads() -> None:
    @lru(maxsize=50)
    def f(x: int) -> int:
        return x

    def hammer() -> None:
        for i in range(2000):
            assert f(i % 100) == i % 100

    ts = [threading.Thread(target=hammer) for _ in range(8)]
    for t in ts: t.start()
    for t in ts: t.join()
    info = f.cache_info()
    assert info.currsize == 50 and info.hits + info.misses == 16000


def test_wrapped_and_params() -> None:
    @lru(maxsize=3)
    def g(a: int) -> int:
        """doc"""
        return a

    assert g.__wrapped__(1) == 1 and g.__doc__ == "doc" and g.__name__ == "g"
    assert g.cache_parameters() == {"maxsize": 3, "typed": False}
