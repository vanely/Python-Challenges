"""T1 w3 — operator overloading done right, NotImplemented, ABCs and goose typing."""
from __future__ import annotations

import functools
import numbers
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


@functools.total_ordering
class Meters:
    def __init__(self, v: float) -> None:
        self.v = float(v)

    def __repr__(self) -> str:
        return f"Meters({self.v})"

    # binary: return NotImplemented for unknown types so Python tries the reflected op
    def __add__(self, other: object) -> Meters:
        if isinstance(other, Meters):
            return Meters(self.v + other.v)
        if isinstance(other, numbers.Real):
            return Meters(self.v + float(other))
        return NotImplemented

    __radd__ = __add__                       # 5 + Meters(1)

    def __mul__(self, k: object) -> Meters:
        if isinstance(k, numbers.Real):
            return Meters(self.v * float(k))
        return NotImplemented

    __rmul__ = __mul__

    def __iadd__(self, other: object) -> Meters:   # in-place: mutate and return self
        if isinstance(other, Meters):
            self.v += other.v
            return self
        return NotImplemented

    def __neg__(self) -> Meters:
        return Meters(-self.v)

    def __abs__(self) -> Meters:
        return Meters(abs(self.v))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Meters):
            return self.v == other.v
        return NotImplemented

    def __lt__(self, other: Meters) -> bool:   # total_ordering derives the rest
        return self.v < other.v

    def __hash__(self) -> int:
        return hash(self.v)

    def __bool__(self) -> bool:
        return self.v != 0

    def __format__(self, spec: str) -> str:
        return f"{self.v:{spec or '.1f'}} m"


m = Meters(2)
print(m + 1, 1 + m, 3 * m, -m, abs(Meters(-1)), m == Meters(2), m <= Meters(3), m >= Meters(1))
m += Meters(1)
print(m, f"{m:.3f}", format(m), bool(Meters(0)))
try:
    m + "x"                                  # mypy allows it (object param); runtime rejects
except TypeError as e:
    print("TypeError:", e)                   # Meters.__add__ returned NotImplemented; str has no __radd__


# --- ABCs: abstract methods, mixins for free, virtual subclasses -----------------------------------
class Tombola(ABC):
    @abstractmethod
    def load(self, items: Iterable[Any]) -> None: ...

    @abstractmethod
    def pick(self) -> Any: ...

    def loaded(self) -> bool:                # concrete mixin built on abstract ones
        return bool(self.inspect())

    def inspect(self) -> tuple[Any, ...]:
        items = []
        while True:
            try:
                items.append(self.pick())
            except LookupError:
                break
        self.load(items)
        return tuple(sorted(items))


class BingoCage(Tombola):
    def __init__(self, items: Iterable[Any]) -> None:
        self._items: list[Any] = []
        self.load(items)

    def load(self, items: Iterable[Any]) -> None:
        self._items.extend(items)

    def pick(self) -> Any:
        try:
            return self._items.pop()
        except IndexError:
            raise LookupError("empty") from None


b = BingoCage([3, 1, 2])
print(b.loaded(), b.inspect(), b.pick())


@Tombola.register                            # goose typing: virtual subclass, no inheritance
class TomboList(list):  # type: ignore[type-arg]
    def load(self, items: Iterable[Any]) -> None:
        self.extend(items)

    def pick(self) -> Any:
        return self.pop()


print(issubclass(TomboList, Tombola), isinstance(TomboList(), Tombola), Tombola.__subclasshook__)


class Sized2(ABC):
    @classmethod
    def __subclasshook__(cls, C: type) -> bool:     # structural check at isinstance time
        return any("__len__" in B.__dict__ for B in C.__mro__)


print(isinstance([], Sized2), isinstance(3, Sized2))
print(isinstance(2.5, numbers.Real), isinstance(True, numbers.Integral))
