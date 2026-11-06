import time
from pathlib import Path

from fetchr.cache import Cache, cached


def test_roundtrip(cache: Cache) -> None:
    cache.set("k", {"a": 1})
    assert cache.get("k") == {"a": 1}
    assert cache.get("missing") is None


def test_ttl_expiry(tmp_path: Path) -> None:
    c = Cache(directory=tmp_path, ttl=0.01)
    c.set("k", 1)
    time.sleep(0.02)
    assert c.get("k") is None


def test_clear(cache: Cache) -> None:
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.clear() == 2
    assert cache.get("a") is None


def test_cached_decorator(cache: Cache) -> None:
    calls = 0

    @cached(cache)
    def expensive(n: int) -> int:
        nonlocal calls
        calls += 1
        return n * 2

    assert expensive(2) == 4
    assert expensive(2) == 4
    assert calls == 1
