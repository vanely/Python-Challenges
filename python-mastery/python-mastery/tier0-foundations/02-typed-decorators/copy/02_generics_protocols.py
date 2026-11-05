"""0.2 — Generics, variance, Protocol vs ABC, overload, narrowing, Self, TypeVarTuple.
mypy --strict passes. Lines that would FAIL are commented with the exact error."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    Self,
    TypeGuard,
    TypeVarTuple,
    Unpack,
    assert_never,
    overload,
    runtime_checkable,
)


# --- variance -------------------------------------------------------------------------------------
class Animal: ...
class Dog(Animal): ...


def feed_all(animals: Sequence[Animal]) -> None: ...        # covariant: read-only view
def add_cat(animals: list[Animal]) -> None: animals.append(Animal())


dogs: list[Dog] = [Dog()]
feed_all(dogs)                     # OK: Sequence is covariant
# add_cat(dogs)                    # error: Argument 1 has incompatible type "list[Dog]"; expected "list[Animal]"


def on_animal(a: Animal) -> None: ...
def on_dog(d: Dog) -> None: ...


handler_for_dogs: Callable[[Dog], None] = on_animal   # OK: contravariant in parameters
# handler_for_animals: Callable[[Animal], None] = on_dog  # error


# --- PEP 695 generics with inferred variance ------------------------------------------------------
class Box[T]:
    def __init__(self, item: T) -> None:
        self.item = item

    def map[U](self, f: Callable[[T], U]) -> Box[U]:
        return Box(f(self.item))


class ReadOnlyBox[T]:                      # only *returns* T -> inferred covariant
    def __init__(self, item: T) -> None:
        self._item = item

    def get(self) -> T:
        return self._item


ro: ReadOnlyBox[Animal] = ReadOnlyBox(Dog())      # OK because covariant
# b: Box[Animal] = Box(Dog())                     # OK too, actually: inference picks Box[Animal]


def first[T](xs: Sequence[T]) -> T:
    return xs[0]


def largest[T: (int, float, str)](xs: Iterable[T]) -> T:   # constrained TypeVar
    return max(xs)


class Comparable(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...


def smallest[C: Comparable](xs: Iterable[C]) -> C:         # bound TypeVar via Protocol
    return min(xs)


# --- Protocol vs ABC ---------------------------------------------------------------------------------
@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...


class Resource:                            # never says "implements Closeable"
    def close(self) -> None:
        print("  closed")


def shutdown(r: Closeable) -> None:
    r.close()


shutdown(Resource())                       # structural: OK
print(isinstance(Resource(), Closeable))   # True — checks method presence only


class Shape(ABC):                          # nominal; can carry implementation
    @abstractmethod
    def area(self) -> float: ...

    def describe(self) -> str:
        return f"{type(self).__name__} with area {self.area():.1f}"


class Sq(Shape):
    def area(self) -> float:
        return 4.0


# Shape()                                  # error + TypeError at runtime: abstract
print(Sq().describe())


# --- overload -----------------------------------------------------------------------------------------
@overload
def load(path: str, *, binary: Literal[True]) -> bytes: ...
@overload
def load(path: str, *, binary: Literal[False] = ...) -> str: ...
def load(path: str, *, binary: bool = False) -> bytes | str:
    return b"" if binary else ""


if TYPE_CHECKING:
    reveal_type(load("x"))                 # str
    reveal_type(load("x", binary=True))    # bytes


# --- narrowing -------------------------------------------------------------------------------------------
def is_str_list(xs: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in xs)


def shout(xs: list[object]) -> None:
    if is_str_list(xs):
        print([x.upper() for x in xs])     # narrowed to list[str]


class Color(Enum):
    RED = 1
    BLUE = 2


def name(c: Color) -> str:
    match c:
        case Color.RED:
            return "red"
        case Color.BLUE:
            return "blue"
        case _:
            assert_never(c)                # add a member to Color -> mypy error here


def describe(x: int | str | None) -> str:
    if x is None:
        return "none"
    if isinstance(x, int):
        return f"int {x}"
    return f"str {x.upper()}"             # narrowed to str by elimination


# --- Self --------------------------------------------------------------------------------------------------
class Builder:
    def __init__(self) -> None:
        self.parts: list[str] = []

    def add(self, p: str) -> Self:        # subclasses get their own type back
        self.parts.append(p)
        return self

    @classmethod
    def create(cls) -> Self:
        return cls()


class FancyBuilder(Builder):
    def fancy(self) -> Self:
        return self.add("*")


if TYPE_CHECKING:
    reveal_type(FancyBuilder.create().add("a").fancy())   # FancyBuilder


# --- TypeVarTuple ----------------------------------------------------------------------------------------
def prepend[T, *Ts](x: T, xs: tuple[*Ts]) -> tuple[T, *Ts]:   # PEP 695 variadic syntax
    return (x, *xs)


Ts = TypeVarTuple("Ts")                     # pre-3.12 spelling of the same thing


def append_old[T](xs: tuple[Unpack[Ts]], x: T) -> tuple[Unpack[Ts], T]:  # type: ignore[valid-type]
    return (*xs, x)


if TYPE_CHECKING:
    reveal_type(prepend(1, ("a", 2.0)))   # tuple[int, str, float]


if __name__ == "__main__":
    print(Box(2).map(str).item, first("ab"), largest([1, 5]), smallest(["b", "a"]))
    shout(["a", "b"])
    print(name(Color.RED), describe(None), describe("x"))
    print(prepend(1, ("a", 2.0)))
