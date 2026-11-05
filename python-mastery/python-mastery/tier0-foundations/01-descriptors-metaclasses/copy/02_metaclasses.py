"""0.1 — Metaclasses and their lighter alternatives. Run + mypy --strict."""
from __future__ import annotations

from typing import Any, ClassVar


# --- 1. A class statement is a call to type() --------------------------------------------------
def greet(self: Any) -> str:
    return f"hi from {self.name}"


Person = type("Person", (), {"name": "ada", "greet": greet, "__module__": __name__})
print(Person().greet(), type(Person), Person.__mro__)


# --- 2. A real metaclass: collect Field-like attributes, in order ------------------------------------
class Field:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"Field({self.name}:{self.kind})"


class SchemaMeta(type):
    @classmethod
    def __prepare__(  # type: ignore[override]  # typeshed declares this differently; runtime is fine
        mcls, name: str, bases: tuple[type, ...], **kw: Any
    ) -> dict[str, Any]:
        print(f"  __prepare__ for {name}")
        return {}                          # could return a custom mapping

    def __new__(
        mcls, name: str, bases: tuple[type, ...], ns: dict[str, Any], **kw: Any
    ) -> SchemaMeta:
        fields = {k: v for k, v in ns.items() if isinstance(v, Field)}
        for base in bases:                 # inherit parent fields first
            fields = {**getattr(base, "_fields", {}), **fields}
        ns["_fields"] = fields
        cls = super().__new__(mcls, name, bases, ns)
        print(f"  created {name} with fields {list(fields)}")
        return cls

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Controls instantiation. Here: enforce keyword-only construction."""
        if args:
            raise TypeError(f"{cls.__name__} takes keyword arguments only")
        return super().__call__(**kwargs)


class Schema(metaclass=SchemaMeta):
    _fields: ClassVar[dict[str, Field]]

    def __init__(self, **values: Any) -> None:
        for k, v in values.items():
            if k not in self._fields:
                raise TypeError(f"unknown field {k!r}")
            setattr(self, k, v)


class User(Schema):
    id = Field("int")
    name = Field("str")


class Admin(User):
    level = Field("int")


print(User._fields, Admin._fields)
print(type(User), isinstance(User, SchemaMeta))
try:
    User(1, "x")                           # type: ignore[call-arg]
except TypeError as e:
    print("metaclass __call__:", e)


# --- 3. The same job WITHOUT a metaclass: __init_subclass__ + __set_name__ ---------------------------
class Model:
    _fields: ClassVar[dict[str, Field]] = {}
    table: ClassVar[str] = ""

    def __init_subclass__(cls, table: str | None = None, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        inherited: dict[str, Field] = {}
        for base in reversed(cls.__mro__[1:]):
            inherited.update(getattr(base, "_fields", {}))
        own = {k: v for k, v in vars(cls).items() if isinstance(v, Field)}
        cls._fields = {**inherited, **own}
        cls.table = table or cls.__name__.lower()


class Post(Model, table="posts"):
    id = Field("int")
    title = Field("str")


class Draft(Post):
    reason = Field("str")


print(Post._fields, Post.table, Draft._fields, Draft.table)
print(type(Post))                                              # plain `type` — no metaclass


# --- 4. Registry metaclass ------------------------------------------------------------------------
class PluginMeta(type):
    registry: ClassVar[dict[str, type]] = {}

    def __init__(cls, name: str, bases: tuple[type, ...], ns: dict[str, Any]) -> None:
        super().__init__(name, bases, ns)
        if bases:                          # skip the abstract root
            PluginMeta.registry[name.lower()] = cls


class Plugin(metaclass=PluginMeta):
    pass


class Csv(Plugin): ...
class Json(Plugin): ...


print(PluginMeta.registry)


# --- 5. Metaclass conflicts: the reason to avoid them ------------------------------------------------
class OtherMeta(type): ...
class X(metaclass=OtherMeta): ...
try:
    class Y(User, X): ...                  # type: ignore[metaclass]  # mypy catches this statically too
except TypeError as e:
    print("conflict:", str(e)[:60], "...")
