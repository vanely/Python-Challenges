"""T1 w4 — iteration protocols, generator plumbing, MRO/cooperative inheritance."""
from __future__ import annotations

import re
from collections.abc import Generator, Iterator


class Sentence:
    """A collection: iterable but NOT its own iterator (fresh iterator per loop)."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __iter__(self) -> Iterator[str]:
        for m in re.finditer(r"\w+", self.text):   # generator function = cheapest iterator
            yield m.group()


s = Sentence("the quick fox")
print(list(s), list(s))                      # both full: independent iterators
it = iter(s)
print(next(it), next(it), list(it), list(it))


# --- generator protocol: send / throw / close ---------------------------------------------------
def averager() -> Generator[float, float, str]:
    total, n = 0.0, 0
    try:
        while True:
            x = yield (total / n if n else 0.0)
            total += x
            n += 1
    except GeneratorExit:
        print("  averager closed after", n)
        raise
    return "unreachable"


g = averager()
next(g)                                      # prime
print(g.send(10), g.send(20))
g.close()                                    # raises GeneratorExit inside


def sub() -> Generator[int, int, str]:
    got = yield 1
    got2 = yield got * 2
    return f"sub saw {got},{got2}"


def outer() -> Generator[int, int, None]:
    result = yield from sub()               # transparently forwards send/throw; captures return
    print("  outer got:", result)


o = outer()
print(next(o), o.send(5), end=" ")
try:
    o.send(7)
except StopIteration:
    print()


# --- MRO and cooperative super() -------------------------------------------------------------------
class Base:
    def greet(self) -> list[str]:
        return ["Base"]


class LoggingMixin:
    def greet(self) -> list[str]:
        return ["Logging", *super().greet()]  # type: ignore[misc]  # mixins call super blindly


class TimingMixin:
    def greet(self) -> list[str]:
        return ["Timing", *super().greet()]  # type: ignore[misc]


class Service(LoggingMixin, TimingMixin, Base):
    def greet(self) -> list[str]:
        return ["Service", *super().greet()]


print([c.__name__ for c in Service.__mro__])
print(Service().greet())


# --- why not to subclass dict for behaviour ------------------------------------------------------------
class UpperDict(dict):  # type: ignore[type-arg]
    def __setitem__(self, k: str, v: object) -> None:
        super().__setitem__(k.upper(), v)


ud = UpperDict(a=1)                          # __init__ is C: bypasses __setitem__
ud["b"] = 2
ud.update(c=3)                               # update is C: bypasses too
print(ud)                                    # {'a': 1, 'B': 2, 'c': 3}  <- inconsistent
