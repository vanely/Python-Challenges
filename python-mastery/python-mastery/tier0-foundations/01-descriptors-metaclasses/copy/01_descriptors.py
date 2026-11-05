"""0.1 — Descriptors. Run: python 01_descriptors.py && mypy --strict 01_descriptors.py"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar, overload

T = TypeVar("T")


# --- 1. The protocol, minimal -----------------------------------------------------------
class Verbose:
    """Non-data descriptor: only __get__. Instance dict can shadow it."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name                      # learns its attribute name at class creation

    def __get__(self, obj: object | None, objtype: type | None = None) -> Any:
        print(f"  __get__ obj={'None' if obj is None else 'inst'} name={self.name}")
        return self if obj is None else 42


class A:
    v = Verbose()


a = A()
print(A.v)          # obj is None -> returns descriptor itself
print(a.v)          # 42
a.__dict__["v"] = "shadowed"
print(a.v)          # instance dict wins over a NON-data descriptor


# --- 2. Data descriptor with per-instance storage ----------------------------------------------
class Positive:
    """Data descriptor (__set__). Wins over instance dict. State lives on the instance."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.public = name
        self.private = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> Positive: ...
    @overload
    def __get__(self, obj: object, objtype: type | None = None) -> float: ...
    def __get__(self, obj: object | None, objtype: type | None = None) -> Positive | float:
        if obj is None:
            return self
        value: float = getattr(obj, self.private)
        return value

    def __set__(self, obj: object, value: float) -> None:
        if value <= 0:
            raise ValueError(f"{self.public} must be positive, got {value}")
        setattr(obj, self.private, value)   # NOT self.value — descriptor is shared


class Order:
    qty = Positive()
    price = Positive()

    def __init__(self, qty: float, price: float) -> None:
        self.qty = qty                      # goes through __set__
        self.price = price


o = Order(2, 9.5)
print(o.qty * o.price, o.__dict__)         # {'_qty': 2, '_price': 9.5}
try:
    o.qty = -1
except ValueError as e:
    print("rejected:", e)


# --- 3. property, classmethod, cached_property — reimplemented -----------------------------------
# Lesson inside the lesson: mypy hard-codes knowledge of the *builtin* property/classmethod. A
# user-defined descriptor with the same shape works at runtime but the checker can't follow the
# rebinding, hence the targeted ignores below. This is why libraries ship .pyi stubs / plugins.
class my_property(Generic[T]):
    def __init__(
        self, fget: Callable[[Any], T], fset: Callable[[Any, T], None] | None = None
    ) -> None:
        self.fget, self.fset = fget, fset
        self.__doc__ = fget.__doc__

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: object | None, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return self.fget(obj)

    def __set__(self, obj: object, value: T) -> None:
        if self.fset is None:
            raise AttributeError(f"property {self.name!r} has no setter")
        self.fset(obj, value)

    def setter(self, fset: Callable[[Any, T], None]) -> my_property[T]:
        return type(self)(self.fget, fset)


class my_classmethod:
    def __init__(self, f: Callable[..., Any]) -> None:
        self.f = f

    def __get__(self, obj: object | None, cls: type | None = None) -> Callable[..., Any]:
        if cls is None:
            cls = type(obj)
        bound: Callable[..., Any] = self.f.__get__(cls, cls)  # bind via the function's own __get__
        return bound


class my_cached_property:
    """Non-data descriptor: computes once, stores in __dict__, then step 2 of lookup wins."""

    def __init__(self, func: Callable[[Any], Any]) -> None:
        self.func = func

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        value = self.func(obj)
        obj.__dict__[self.name] = value     # cache; requires a __dict__ (no __slots__)
        return value


class Circle:
    def __init__(self, r: float) -> None:
        self._r = r

    @my_property
    def r(self) -> float:
        """radius"""
        return self._r

    @r.setter                              # type: ignore[no-redef]  # mypy special-cases builtin property; not ours
    def r(self, v: float) -> None:
        self._r = v

    @my_classmethod                        # same: mypy only understands the real classmethod
    def unit(cls) -> Circle:
        return cls(1.0)                    # type: ignore[operator,no-any-return]

    @my_cached_property
    def area(self) -> float:
        print("  computing area")
        return 3.14159 * self._r**2


c = Circle.unit()
c.r = 2
print(c.r, c.area, c.area, "area" in c.__dict__)


# --- 4. Functions are descriptors: this is how methods bind --------------------------------------
def f(self: object) -> str:
    return f"bound to {type(self).__name__}"


class B:
    pass


B.m = f                                    # type: ignore[attr-defined]
print(B().m())                             # type: ignore[attr-defined]
print(f.__get__(B(), B))                   # same thing, by hand
print(B.__dict__["m"] is f)                # the raw function lives in the class dict
