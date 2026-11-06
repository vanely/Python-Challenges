"""Step 2: the cache. Spec: steps/02-cache.md."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from fetchr.cache import Cache, cached


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(directory=tmp_path / "c", ttl=60)


def test_roundtrip_and_miss(cache: Cache) -> None:
    cache.set("k", {"a": [1, 2]})
    assert cache.get("k") == {"a": [1, 2]}
    assert cache.get("missing") is None
    sentinel = object()
    assert cache.get("missing", sentinel) is sentinel


def test_creates_its_directory(tmp_path: Path) -> None:
    Cache(directory=tmp_path / "deep" / "er")
    assert (tmp_path / "deep" / "er").is_dir()


def test_default_directory_comes_from_env_at_construction_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "from-env"
    monkeypatch.setenv("FETCHR_CACHE_DIR", str(target))
    c = Cache()
    assert c.directory == target and target.is_dir()


def test_ttl_expiry_uses_file_age(cache: Cache) -> None:
    cache.set("k", 1)
    (f,) = list(cache.directory.glob("*.json"))
    old = time.time() - 3600
    os.utime(f, (old, old))
    assert cache.get("k") is None
    assert not f.exists(), "an expired entry is deleted when read"


def test_corrupt_file_is_a_miss_not_a_crash(cache: Cache) -> None:
    cache.set("k", {"a": 1})
    for f in cache.directory.glob("*.json"):
        f.write_text('{"a": ', encoding="utf-8")  # truncated write
    assert cache.get("k") is None


def test_set_leaves_no_temp_files(cache: Cache) -> None:
    for i in range(5):
        cache.set(f"k{i}", i)
    names = sorted(p.name for p in cache.directory.iterdir())
    assert len(names) == 5 and all(n.endswith(".json") for n in names), names


def test_clear_returns_count(cache: Cache) -> None:
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.clear() == 2
    assert cache.get("a") is None
    assert cache.clear() == 0


def test_keys_with_unsafe_characters(cache: Cache) -> None:
    key = "/repos/o/r?[('page', 1)] \\ : * ? \" < > |"
    cache.set(key, "ok")
    assert cache.get(key) == "ok"


def test_cached_calls_once_per_arguments(cache: Cache) -> None:
    calls: list[int] = []

    @cached(cache)
    def double(n: int) -> int:
        calls.append(n)
        return n * 2

    assert double(2) == 4
    assert double(2) == 4
    assert double(3) == 6
    assert calls == [2, 3]


def test_cached_caches_none_results(cache: Cache) -> None:
    calls = 0

    @cached(cache)
    def nothing() -> None:
        nonlocal calls
        calls += 1

    nothing()
    nothing()
    assert calls == 1, "a cached None is still a hit; use a sentinel, not `is None`"


def test_cached_preserves_metadata(cache: Cache) -> None:
    @cached(cache)
    def documented(x: int) -> int:
        """Docstring survives."""
        return x

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docstring survives."
    assert documented.__wrapped__ is not None  # type: ignore[attr-defined]


def test_cached_distinguishes_functions_with_same_args(cache: Cache) -> None:
    @cached(cache)
    def f(x: int) -> str:
        return "f"

    @cached(cache)
    def g(x: int) -> str:
        return "g"

    assert (f(1), g(1)) == ("f", "g")
