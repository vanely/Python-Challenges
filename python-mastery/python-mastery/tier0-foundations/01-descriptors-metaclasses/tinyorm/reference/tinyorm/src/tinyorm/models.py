"""ModelBase metaclass, Manager descriptor, Model base class."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, overload

from tinyorm.db import Database
from tinyorm.exceptions import DoesNotExist
from tinyorm.fields import Field, IntegerField
from tinyorm.query import QuerySet

M = TypeVar("M", bound="Model")


@dataclass
class Options:
    table: str
    fields: dict[str, Field]
    abstract: bool = False
    _pk: Field | None = None

    @property
    def pk(self) -> Field:
        if self._pk is None:
            raise TypeError("abstract models have no primary key")
        pk_field: Field = self._pk
        return pk_field


class Manager(Generic[M]):
    """Descriptor accessible on the class only — like Django's Manager."""

    def __init__(self) -> None:
        self.model: type[M] | None = None

    def contribute_to_class(self, model: type[M]) -> None:
        self.model = model

    @overload
    def __get__(self, obj: None, objtype: type[M]) -> Manager[M]: ...
    @overload
    def __get__(self, obj: M, objtype: type[M]) -> Manager[M]: ...
    def __get__(self, obj: M | None, objtype: type[M] | None = None) -> Manager[M]:
        if obj is not None:
            raise AttributeError("Manager isn't accessible via instances")
        return self

    def get_queryset(self) -> QuerySet[M]:
        assert self.model is not None
        return QuerySet(self.model)

    def all(self) -> QuerySet[M]:
        return self.get_queryset()

    def filter(self, **kw: Any) -> QuerySet[M]:
        return self.get_queryset().filter(**kw)

    def exclude(self, **kw: Any) -> QuerySet[M]:
        return self.get_queryset().exclude(**kw)

    def order_by(self, *names: str) -> QuerySet[M]:
        return self.get_queryset().order_by(*names)

    def get(self, **kw: Any) -> M:
        return self.get_queryset().get(**kw)

    def create(self, **kw: Any) -> M:
        assert self.model is not None
        obj = self.model(**kw)
        obj.save()
        return obj

    def count(self) -> int:
        return self.get_queryset().count()


class ModelBase(type):
    """Collects fields, builds _meta, attaches a Manager and a per-model DoesNotExist."""

    def __new__(
        mcls, name: str, bases: tuple[type, ...], ns: dict[str, Any], **kw: Any
    ) -> ModelBase:
        # Mirror Django: create the class with a minimal namespace, then add attributes.
        meta_cls = ns.pop("Meta", None)
        attrs = {k: v for k, v in ns.items() if not isinstance(v, Field | Manager)}
        cls = super().__new__(mcls, name, bases, attrs, **kw)

        abstract = bool(getattr(meta_cls, "abstract", False))
        fields: dict[str, Field] = {}
        for base in reversed(cls.__mro__[1:]):
            parent_meta = base.__dict__.get("_meta")
            if isinstance(parent_meta, Options):
                fields.update(parent_meta.fields)
        own_fields = {k: v for k, v in ns.items() if isinstance(v, Field)}

        if name != "Model" and not abstract and not own_fields.get("id"):
            has_pk = any(f.primary_key for f in {**fields, **own_fields}.values())
            if not has_pk:
                own_fields = {"id": IntegerField(primary_key=True), **own_fields}

        for fname, f in own_fields.items():
            setattr(cls, fname, f)  # type.__setattr__ doesn't call __set_name__
            f.__set_name__(cls, fname)
            fields[fname] = f

        if name != "Model":
            table = getattr(meta_cls, "table", name.lower())
            pk = next((f for f in fields.values() if f.primary_key), None)
            # Attributes on the *class being built*: the metaclass's static type doesn't know
            # about Model's ClassVars, so we go through setattr (B010 is about safety, not typing).
            setattr(cls, "_meta", Options(table=table, fields=fields, abstract=abstract, _pk=pk))  # noqa: B010
        if name != "Model" and not abstract:
            manager = next((v for v in ns.values() if isinstance(v, Manager)), Manager())
            manager.contribute_to_class(cls)
            setattr(cls, "objects", manager)  # noqa: B010
            dne = type("DoesNotExist", (DoesNotExist,), {"__module__": cls.__module__})
            setattr(cls, "DoesNotExist", dne)  # noqa: B010
        return cls


class Model(metaclass=ModelBase):
    _meta: ClassVar[Options]
    objects: ClassVar[Manager[Any]]
    DoesNotExist: ClassVar[type[DoesNotExist]]

    def __init__(self, **values: Any) -> None:
        for fname, f in self._meta.fields.items():
            if fname in values:
                setattr(self, fname, values.pop(fname))
            else:
                setattr(self, fname, f.get_default())
        if values:
            raise TypeError(f"{type(self).__name__} got unexpected fields {sorted(values)}")

    # --- persistence ---------------------------------------------------------------------
    @property
    def pk(self) -> Any:
        return getattr(self, self._meta.pk.name)

    def save(self) -> None:
        meta = self._meta
        db = Database.get_default()
        data = {n: f.to_db(getattr(self, n)) for n, f in meta.fields.items()}
        with db.transaction():
            if self.pk is None:
                data.pop(meta.pk.name)
                cols = ", ".join(f'"{c}"' for c in data)
                marks = ", ".join("?" * len(data))
                cur = db.execute(
                    f'INSERT INTO "{meta.table}" ({cols}) VALUES ({marks})', tuple(data.values())
                )
                setattr(self, meta.pk.name, cur.lastrowid)
            else:
                pk_val = data.pop(meta.pk.name)
                sets = ", ".join(f'"{c}" = ?' for c in data)
                db.execute(
                    f'UPDATE "{meta.table}" SET {sets} WHERE "{meta.pk.name}" = ?',
                    (*data.values(), pk_val),
                )

    def delete(self) -> None:
        if self.pk is None:
            raise ValueError("unsaved object")
        meta = self._meta
        db = Database.get_default()
        with db.transaction():
            db.execute(f'DELETE FROM "{meta.table}" WHERE "{meta.pk.name}" = ?', (self.pk,))
        setattr(self, meta.pk.name, None)

    def refresh_from_db(self) -> None:
        fresh = type(self).objects.get(pk=self.pk)
        for n in self._meta.fields:
            setattr(self, n, getattr(fresh, n))

    @classmethod
    def _from_row(cls: type[M], row: sqlite3.Row) -> M:
        obj = cls.__new__(cls)
        for n, f in cls._meta.fields.items():
            obj.__dict__[f.attr] = f.from_db(row[n])
        return obj

    # --- dunders -------------------------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Model) or type(other) is not type(self):
            return NotImplemented
        return self.pk is not None and bool(self.pk == other.pk)

    def __hash__(self) -> int:
        if self.pk is None:
            raise TypeError("unsaved model instances are unhashable")
        return hash((type(self), self.pk))

    def __repr__(self) -> str:
        vals = ", ".join(f"{n}={getattr(self, n)!r}" for n in self._meta.fields)
        return f"{type(self).__name__}({vals})"
