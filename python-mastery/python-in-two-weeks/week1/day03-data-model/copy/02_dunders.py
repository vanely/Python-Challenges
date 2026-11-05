"""Day 3 — making objects behave like builtins."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    cents: int
    currency: str = "USD"

    def __add__(self, other: Money) -> Money:
        if other.currency != self.currency:
            raise ValueError("currency mismatch")
        return Money(self.cents + other.cents, self.currency)

    def __mul__(self, k: int) -> Money:
        return Money(self.cents * k, self.currency)

    __rmul__ = __mul__          # so 3 * money works

    def __bool__(self) -> bool:
        return self.cents != 0

    def __str__(self) -> str:
        return f"{self.cents / 100:.2f} {self.currency}"


m = Money(150) + Money(250)
print(m, repr(m), 3 * m, bool(Money(0)))


class Playlist:
    """A container: len, index, slice, contains, iterate, call."""

    def __init__(self, *tracks: str) -> None:
        self._tracks = list(tracks)

    def __len__(self) -> int:
        return len(self._tracks)

    def __getitem__(self, i: int | slice) -> str | list[str]:
        return self._tracks[i]          # slicing comes for free by delegating

    def __contains__(self, t: str) -> bool:
        return t in self._tracks

    def __iter__(self) -> Iterator[str]:
        return iter(self._tracks)

    def __repr__(self) -> str:
        return f"Playlist({', '.join(map(repr, self._tracks))})"

    def __call__(self) -> str:
        return f"now playing {self._tracks[0]}"

    @property
    def first(self) -> str:
        return self._tracks[0]

    @first.setter
    def first(self, value: str) -> None:
        if not value:
            raise ValueError("empty")
        self._tracks[0] = value


pl = Playlist("a", "b", "c")
print(len(pl), pl[0], pl[-1], pl[1:], "b" in pl, list(pl), pl)
print(pl())
pl.first = "z"
print(pl.first)
for t in pl:
    print(t, end=" ")
print()


class Temperature:
    """@property for validation and computed attributes."""

    def __init__(self, celsius: float) -> None:
        self.celsius = celsius          # goes through the setter

    @property
    def celsius(self) -> float:
        return self._c

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._c = value

    @property
    def fahrenheit(self) -> float:
        return self._c * 9 / 5 + 32

    @staticmethod
    def is_freezing(c: float) -> bool:
        return c <= 0


temp = Temperature(25)
print(temp.fahrenheit, Temperature.is_freezing(-1))
