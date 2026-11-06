"""T1 w1 — the sequence/collection protocols and what you get for free."""
from __future__ import annotations

import bisect
import itertools
from collections import ChainMap, UserDict
from collections.abc import Iterator, Sequence
from typing import Any, overload


class Deck(Sequence[str]):
    """Implement __len__ and __getitem__; Sequence supplies the rest."""

    ranks = [str(n) for n in range(2, 11)] + list("JQKA")
    suits = ["spades", "hearts", "diamonds", "clubs"]

    def __init__(self) -> None:
        self._cards = [f"{r} of {s}" for s in self.suits for r in self.ranks]

    def __len__(self) -> int:
        return len(self._cards)

    @overload
    def __getitem__(self, i: int) -> str: ...
    @overload
    def __getitem__(self, i: slice) -> Sequence[str]: ...
    def __getitem__(self, i: int | slice) -> str | Sequence[str]:
        return self._cards[i]


d = Deck()
print(len(d), d[0], d[-1], d[12:15])
print("A of spades" in d)                   # __contains__ from Sequence mixin
print(list(reversed(d))[:2])                # __reversed__ mixin
print(d.index("K of hearts"), d.count("2 of clubs"))
for card in itertools.islice(d, 3):         # __iter__ mixin via __getitem__ (d[:3] would be a list)
    print(" ", card)

# special methods are looked up on the TYPE
d.__len__ = lambda: 0                       # type: ignore[method-assign]
print(len(d))                               # still 52


# --- __missing__ is consulted by __getitem__ only ----------------------------------------------
class StrKeyDict(UserDict[str, Any]):       # UserDict, not dict: dict's C methods skip overrides
    def __missing__(self, key: object) -> Any:
        if isinstance(key, str):
            raise KeyError(key)
        return self[str(key)]

    def __contains__(self, key: object) -> bool:
        return str(key) in self.data


sk = StrKeyDict({"1": "one"})
k: Any = 1                                  # Any: we're deliberately abusing the key type
print(sk[k], sk.get(k, "default"), k in sk)   # get() also works because UserDict.get calls __getitem__


# --- hashability contract --------------------------------------------------------------------------
class Money:
    def __init__(self, cents: int) -> None:
        self.cents = cents

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Money) and other.cents == self.cents

    def __hash__(self) -> int:              # equal objects MUST hash equal; define both or neither
        return hash(self.cents)


print(len({Money(1), Money(1), Money(2)}))


# --- += vs + -------------------------------------------------------------------------------------------
a = [1]
b = a
a += [2]                                    # __iadd__: in place; b sees it
print(b)
t: tuple[int, ...] = (1,)
u = t
t += (2,)                                   # no __iadd__ on tuple: new object, rebind
print(u, t)

# --- bisect, ChainMap --------------------------------------------------------------------------------
scores = [60, 70, 80, 90]
grades = "FDCBA"
print([grades[bisect.bisect(scores, s)] for s in (55, 70, 85, 95)])
defaults = {"color": "red", "size": 1}
overrides: dict[str, Any] = {"size": 2}
cm = ChainMap(overrides, defaults)
print(cm["color"], cm["size"], dict(cm))


def walk(it: Iterator[int]) -> None: ...
