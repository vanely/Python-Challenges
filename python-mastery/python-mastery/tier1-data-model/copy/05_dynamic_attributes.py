"""T1 w5 — __getattr__/__getattribute__/__setattr__/__dir__, __slots__, property factories."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class Frozen:
    """Attribute-style access to nested mappings, read-only after construction."""

    __slots__ = ("_data", "_frozen")

    def __init__(self, data: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_data", dict(data))
        object.__setattr__(self, "_frozen", True)

    def __getattr__(self, name: str) -> Any:     # called only when normal lookup FAILS
        try:
            v = self._data[name]
        except KeyError:
            raise AttributeError(f"{type(self).__name__} has no attribute {name!r}") from None
        return Frozen(v) if isinstance(v, Mapping) else v

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("frozen")
        object.__setattr__(self, name, value)

    def __dir__(self) -> list[str]:              # tab completion + dir() see the keys
        return sorted(self._data)

    def __repr__(self) -> str:
        return f"Frozen({self._data!r})"


cfg = Frozen({"db": {"host": "x", "port": 5432}, "debug": True})
print(cfg.db.host, cfg.debug, dir(cfg))
try:
    cfg.debug = False
except AttributeError as e:
    print("blocked:", e)
try:
    cfg.nope
except AttributeError as e:
    print(e)
try:
    cfg.extra = 1                            # __slots__ AND __setattr__ both block this
except AttributeError as e:
    print("slots+setattr:", e)


class Trace:
    """__getattribute__ intercepts EVERYTHING — including self.x inside itself (recursion trap)."""

    def __init__(self) -> None:
        self.n = 0

    def __getattribute__(self, name: str) -> Any:
        if not name.startswith("_"):
            print(f"  access {name}")
        return object.__getattribute__(self, name)   # never self.name here


Trace().n


# --- property factory: closures making descriptors (pre-descriptor-class technique) -----------------
def quantity(name: str) -> property:
    key = f"_{name}"

    def getter(self: Any) -> float:
        return getattr(self, key)  # type: ignore[no-any-return]

    def setter(self: Any, value: float) -> None:
        if value <= 0:
            raise ValueError(f"{name} must be > 0")
        setattr(self, key, value)

    return property(getter, setter)


class Item:
    weight = quantity("weight")
    price = quantity("price")

    def __init__(self, w: float, p: float) -> None:
        self.weight, self.price = w, p


i = Item(1, 2)
print(i.weight * i.price, Item.weight)
try:
    i.price = 0
except ValueError as e:
    print(e)

# --- __slots__ costs -------------------------------------------------------------------------------------
import sys


class P:
    def __init__(self) -> None:
        self.x = 1


class S:
    __slots__ = ("x",)

    def __init__(self) -> None:
        self.x = 1


print(sys.getsizeof(P()) + sys.getsizeof(P().__dict__), sys.getsizeof(S()), hasattr(S(), "__dict__"))
