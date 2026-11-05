"""lru — functools.lru_cache reimplemented. Circular doubly-linked list + dict, RLock, typed keys."""

from __future__ import annotations

import functools
import threading
from collections.abc import Callable, Hashable
from typing import Any, Generic, NamedTuple, ParamSpec, TypeVar, overload

P = ParamSpec("P")
R = TypeVar("R")

_PREV, _NEXT, _KEY, _RESULT = 0, 1, 2, 3
_KWD_MARK = object()


class CacheInfo(NamedTuple):
    hits: int
    misses: int
    maxsize: int | None
    currsize: int


class _HashedSeq(list):  # type: ignore[type-arg]
    """Cache the hash: keys are hashed on every lookup, so compute once (like functools)."""

    __slots__ = ("hashvalue",)

    def __init__(self, tup: tuple[Any, ...]) -> None:
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self) -> int:  # type: ignore[override]
        return self.hashvalue


def _make_key(args: tuple[Any, ...], kwds: dict[str, Any], typed: bool) -> Hashable:
    key: tuple[Any, ...] = args
    if kwds:
        key += (_KWD_MARK, *sorted(kwds.items()))
    if typed:
        key += tuple(type(v) for v in args)
        if kwds:
            key += tuple(type(v) for _, v in sorted(kwds.items()))
    if len(key) == 1 and type(key[0]) in {int, str}:
        first: Hashable = key[0]
        return first                           # fast path: the value is its own key
    return _HashedSeq(key)


class LruWrapper(Generic[P, R]):
    def __init__(self, fn: Callable[P, R], maxsize: int | None, typed: bool) -> None:
        functools.update_wrapper(self, fn)
        self.__wrapped__ = fn
        self._maxsize, self._typed = maxsize, typed
        self._cache: dict[Hashable, list[Any]] = {}
        self._lock = threading.RLock()
        self._hits = self._misses = 0
        # circular doubly-linked list; root.next is oldest, root.prev is newest
        self._root: list[Any] = []
        self._root[:] = [self._root, self._root, None, None]

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        key = _make_key(args, kwargs, self._typed)
        with self._lock:
            link = self._cache.get(key)
            if link is not None:
                # move to most-recent position
                prev, nxt, _, result = link
                prev[_NEXT] = nxt
                nxt[_PREV] = prev
                last = self._root[_PREV]
                last[_NEXT] = self._root[_PREV] = link
                link[_PREV] = last
                link[_NEXT] = self._root
                self._hits += 1
                return result  # type: ignore[no-any-return]
            self._misses += 1
        result = self.__wrapped__(*args, **kwargs)      # outside the lock: no poisoning on raise
        with self._lock:
            if key in self._cache:
                pass                                     # another thread filled it meanwhile
            elif self._maxsize is None or len(self._cache) < self._maxsize:
                last = self._root[_PREV]
                link = [last, self._root, key, result]
                last[_NEXT] = self._root[_PREV] = self._cache[key] = link
            else:
                # reuse the oldest link as the new root (the functools trick: no allocation)
                oldroot = self._root
                oldroot[_KEY], oldroot[_RESULT] = key, result
                self._root = oldroot[_NEXT]
                oldkey = self._root[_KEY]
                self._root[_KEY] = self._root[_RESULT] = None
                del self._cache[oldkey]
                self._cache[key] = oldroot
        return result

    def cache_info(self) -> CacheInfo:
        with self._lock:
            return CacheInfo(self._hits, self._misses, self._maxsize, len(self._cache))

    def cache_clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._root[:] = [self._root, self._root, None, None]
            self._hits = self._misses = 0

    def cache_parameters(self) -> dict[str, Any]:
        return {"maxsize": self._maxsize, "typed": self._typed}


@overload
def lru(fn: Callable[P, R], /) -> LruWrapper[P, R]: ...
@overload
def lru(*, maxsize: int | None = 128, typed: bool = False) -> Callable[[Callable[P, R]], LruWrapper[P, R]]: ...
def lru(fn: Callable[P, R] | None = None, /, *, maxsize: int | None = 128, typed: bool = False) -> Any:
    if maxsize is not None and maxsize < 0:
        maxsize = 0

    def deco(f: Callable[P, R]) -> LruWrapper[P, R]:
        return LruWrapper(f, maxsize, typed)

    return deco if fn is None else deco(fn)
