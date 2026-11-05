"""Day 3 — typing for a TS developer. Run: mypy --strict 03_typing.py"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Literal, Protocol, TypeVar, cast, overload

# --- builtin generics, unions, literals -------------------------------------
Scores = dict[str, list[float]]
SortDir = Literal["asc", "desc"]


def mean(xs: Sequence[float]) -> float:            # accept any sequence
    return sum(xs) / len(xs) if xs else 0.0


def sort_names(names: Iterable[str], direction: SortDir = "asc") -> list[str]:
    return sorted(names, reverse=direction == "desc")


def find(users: Mapping[int, str], uid: int) -> str | None:
    return users.get(uid)


name = find({1: "ada"}, 1)
# print(name.upper())        # mypy: Item "None" of "str | None" has no attribute "upper"
if name is not None:
    print(name.upper())      # narrowed


# --- Protocol: structural typing (TS interfaces) -----------------------------
class SupportsArea(Protocol):
    def area(self) -> float: ...


class Square:
    def __init__(self, side: float) -> None:
        self.side = side

    def area(self) -> float:
        return self.side**2


class Circle:
    def __init__(self, r: float) -> None:
        self.r = r

    def area(self) -> float:
        return 3.14159 * self.r**2


def total_area(shapes: Iterable[SupportsArea]) -> float:
    return sum(s.area() for s in shapes)       # neither class "implements" anything


print(total_area([Square(2), Circle(1)]))


# --- generics --------------------------------------------------------------------
T = TypeVar("T")


def first(xs: Sequence[T]) -> T:
    return xs[0]


def first_312[U](xs: Sequence[U]) -> U:        # 3.12 syntax, same thing
    return xs[0]


reveal_int = first([1, 2])          # mypy infers int
reveal_str = first_312("ab")        # str
print(reveal_int, reveal_str)

K = TypeVar("K")
V = TypeVar("V")


def group_by(items: Iterable[V], key: Callable[[V], K]) -> dict[K, list[V]]:
    out: dict[K, list[V]] = {}
    for item in items:
        out.setdefault(key(item), []).append(item)
    return out


print(group_by(["apple", "avocado", "berry"], key=lambda s: s[0]))


# --- overload: many signatures, one implementation ---------------------------------
@overload
def parse(v: str) -> int: ...
@overload
def parse(v: list[str]) -> list[int]: ...
def parse(v: str | list[str]) -> int | list[int]:
    if isinstance(v, str):
        return int(v)
    return [int(x) for x in v]


print(parse("4"), parse(["1", "2"]))


# --- Any, object, cast ------------------------------------------------------------
def load_json() -> Any:              # what json.loads returns
    return {"n": 1}


data = load_json()
n = cast(int, data["n"])             # `as` — no runtime effect
print(n + 1)


def describe(x: object) -> str:      # `unknown`: must narrow before use
    if isinstance(x, int):
        return f"int {x}"
    return f"other {type(x).__name__}"


print(describe(1), describe("s"))
