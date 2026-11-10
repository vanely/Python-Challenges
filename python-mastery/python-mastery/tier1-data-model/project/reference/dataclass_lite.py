"""@record — a dataclass reimplementation that generates methods via exec, like the real one."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import Any, ClassVar, TypeVar, dataclass_transform, get_type_hints, overload

if sys.version_info >= (3, 14):
    import annotationlib

T = TypeVar("T", bound=type)
_MISSING = object()
_FIELDS = "__record_fields__"


class Field:
    __slots__ = ("compare", "default", "default_factory", "name", "repr", "type")

    def __init__(self, default: Any, default_factory: Callable[[], Any] | None, repr: bool, compare: bool) -> None:
        self.default, self.default_factory, self.repr, self.compare = default, default_factory, repr, compare
        self.name = ""
        self.type: Any = None

    @property
    def has_default(self) -> bool:
        return self.default is not _MISSING or self.default_factory is not None

    def __repr__(self) -> str:
        return f"Field({self.name!r})"


def field(*, default: Any = _MISSING, default_factory: Callable[[], Any] | None = None,
          repr: bool = True, compare: bool = True) -> Any:
    if default is not _MISSING and default_factory is not None:
        raise ValueError("cannot specify both default and default_factory")
    return Field(default, default_factory, repr, compare)


def _create_fn(name: str, args: list[str], body: list[str], globals_: dict[str, Any], locals_: dict[str, Any]) -> Any:
    """Build source text and exec it — the technique dataclasses uses. Locals are injected via a
    closure so defaults/factories are captured by reference, not stringified."""
    body_src = "\n".join(f"    {line}" for line in body) or "    pass"
    src = f"def __make__({', '.join(locals_)}):\n def {name}({', '.join(args)}):\n{body_src}\n return {name}"
    src = src.replace("\n    ", "\n  ")
    ns: dict[str, Any] = {}
    exec(src, globals_, ns)                 # noqa: S102
    return ns["__make__"](**locals_)


def _collect_fields(cls: type) -> dict[str, Field]:
    fields: dict[str, Field] = {}
    for base in reversed(cls.__mro__[1:]):
        fields.update(getattr(base, _FIELDS, {}))
    # 3.14 (PEP 649/749): the class body stores __annotate__, not __annotations__, in cls.__dict__
    if sys.version_info >= (3, 14):
        ann = annotationlib.get_annotations(cls, format=annotationlib.Format.FORWARDREF)
    else:
        ann = cls.__dict__.get("__annotations__", {})
    hints = get_type_hints(cls) if ann else {}
    for name, typ in ann.items():
        if getattr(typ, "__origin__", None) is ClassVar or typ is ClassVar:
            continue
        default = cls.__dict__.get(name, _MISSING)
        f = default if isinstance(default, Field) else Field(default, None, True, True)
        if isinstance(f.default, list | dict | set):
            raise ValueError(f"mutable default for field {name!r}; use default_factory")
        f.name, f.type = name, hints.get(name, typ)
        fields[name] = f
        if isinstance(default, Field):
            delattr(cls, name) if f.default is _MISSING else setattr(cls, name, f.default)
    return fields


def _process(cls: type, *, frozen: bool, slots: bool, eq: bool, repr_: bool) -> type:
    fields = _collect_fields(cls)
    setattr(cls, _FIELDS, fields)
    g = sys.modules[cls.__module__].__dict__
    locs: dict[str, Any] = {"_MISSING": _MISSING, "FrozenInstanceError": FrozenInstanceError}

    # __init__ — defaults referenced by name via the injected locals
    args, body = ["self"], []
    seen_default = False
    for f in fields.values():
        if f.default_factory is not None:
            locs[f"_dflt_{f.name}"] = f.default_factory
            args.append(f"{f.name}=_MISSING")
            body.append(f"if {f.name} is _MISSING: {f.name} = _dflt_{f.name}()")
            seen_default = True
        elif f.default is not _MISSING:
            locs[f"_dflt_{f.name}"] = f.default
            args.append(f"{f.name}=_dflt_{f.name}")
            seen_default = True
        else:
            if seen_default:
                raise TypeError(f"non-default field {f.name!r} follows default field")
            args.append(f.name)
        body.append(f"object.__setattr__(self, {f.name!r}, {f.name})" if frozen else f"self.{f.name} = {f.name}")
    cls.__init__ = _create_fn("__init__", args, body, g, locs)  # type: ignore[misc]

    if repr_:
        parts = " + ', ' + ".join(f"'{f.name}=' + repr(self.{f.name})" for f in fields.values() if f.repr) or "''"
        cls.__repr__ = _create_fn("__repr__", ["self"], [f"return type(self).__name__ + '(' + {parts} + ')'"], g, locs)  # type: ignore[method-assign]
    if eq:
        tup = "(" + "".join(f"self.{f.name}," for f in fields.values() if f.compare) + ")"
        otup = tup.replace("self.", "other.")
        cls.__eq__ = _create_fn("__eq__", ["self", "other"],  # type: ignore[method-assign]
                                ["if other.__class__ is not self.__class__: return NotImplemented",
                                 f"return {tup} == {otup}"], g, locs)
        cls.__hash__ = _create_fn("__hash__", ["self"], [f"return hash({tup})"], g, locs) if frozen else None  # type: ignore[method-assign,assignment]
    if frozen:
        cls.__setattr__ = _create_fn("__setattr__", ["self", "name", "value"], ["raise FrozenInstanceError(f'cannot assign to field {name!r}')"], g, locs)  # type: ignore[method-assign]
        cls.__delattr__ = _create_fn("__delattr__", ["self", "name"], ["raise FrozenInstanceError(f'cannot delete field {name!r}')"], g, locs)  # type: ignore[method-assign]
    cls.__match_args__ = tuple(fields)  # type: ignore[attr-defined,misc]

    if slots:
        cls = _add_slots(cls, tuple(fields))
    return cls


def _add_slots(cls: type, names: tuple[str, ...]) -> type:
    """You can't add __slots__ to an existing class: rebuild it (dataclasses._add_slots does this)."""
    ns = {k: v for k, v in cls.__dict__.items() if k not in {"__dict__", "__weakref__"}}
    inherited = {s for b in cls.__mro__[1:] for s in getattr(b, "__slots__", ())}
    ns["__slots__"] = tuple(n for n in names if n not in inherited)
    for n in ns["__slots__"]:
        ns.pop(n, None)                     # class-level defaults conflict with slot descriptors
    new = type(cls)(cls.__name__, cls.__bases__, ns)
    new.__qualname__ = cls.__qualname__
    # functions' __closure__/__class__ cells still point at the old class; fine for our purposes
    return new


@dataclass_transform(field_specifiers=(field, Field))
@overload
def record(cls: T, /) -> T: ...
@dataclass_transform(field_specifiers=(field, Field))
@overload
def record(*, frozen: bool = False, slots: bool = False, eq: bool = True, repr: bool = True) -> Callable[[T], T]: ...
def record(cls: T | None = None, /, *, frozen: bool = False, slots: bool = False, eq: bool = True, repr: bool = True) -> Any:
    def wrap(c: T) -> T:
        return _process(c, frozen=frozen, slots=slots, eq=eq, repr_=repr)  # type: ignore[return-value]

    return wrap if cls is None else wrap(cls)


# --- helpers ------------------------------------------------------------------------------------------
def fields(obj: object) -> tuple[Field, ...]:
    return tuple(getattr(obj if isinstance(obj, type) else type(obj), _FIELDS).values())


def asdict(obj: object) -> dict[str, Any]:
    return {f.name: getattr(obj, f.name) for f in fields(obj)}


def replace(obj: Any, **changes: Any) -> Any:
    return type(obj)(**{**asdict(obj), **changes})
