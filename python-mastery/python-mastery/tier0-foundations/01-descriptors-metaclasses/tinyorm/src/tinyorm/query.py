"""Lazy, immutable QuerySet. SQL is compiled on evaluation; results cached per instance."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from tinyorm.db import Database
from tinyorm.exceptions import DoesNotExist, MultipleObjectsReturned

if TYPE_CHECKING:
    from tinyorm.models import Model

M = TypeVar("M", bound="Model")

_OPS = {
    "exact": "=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


@dataclass(frozen=True)
class Where:
    sql: str
    params: tuple[Any, ...]


def _compile_lookup(model: type[Model], key: str, value: Any) -> Where:
    name, _, op = key.partition("__")
    op = op or "exact"
    if name == "pk":
        name = model._meta.pk.name
    if name not in model._meta.fields:
        raise ValueError(f"{model.__name__} has no field {name!r}")
    col = f'"{name}"'
    fld = model._meta.fields[name]
    if op in _OPS:
        return Where(f"{col} {_OPS[op]} ?", (fld.to_db(value),))
    if op == "contains":
        return Where(f"{col} LIKE ?", (f"%{value}%",))
    if op == "startswith":
        return Where(f"{col} LIKE ?", (f"{value}%",))
    if op == "in":
        vals = tuple(fld.to_db(v) for v in value)
        if not vals:
            return Where("0", ())
        return Where(f"{col} IN ({', '.join('?' * len(vals))})", vals)
    if op == "isnull":
        return Where(f"{col} IS {'' if value else 'NOT '}NULL", ())
    raise ValueError(f"unsupported lookup {op!r}")


@dataclass(frozen=True)
class QuerySet(Generic[M]):
    model: type[M]
    _where: tuple[Where, ...] = ()
    _order: tuple[str, ...] = ()
    _limit: int | None = None
    _offset: int = 0
    _cache: list[M] | None = field(default=None, compare=False, hash=False)

    # --- chaining (each returns a NEW queryset) ------------------------------------------------
    def filter(self, **lookups: Any) -> QuerySet[M]:
        wheres = tuple(_compile_lookup(self.model, k, v) for k, v in lookups.items())
        return replace(self, _where=self._where + wheres, _cache=None)

    def exclude(self, **lookups: Any) -> QuerySet[M]:
        inner = [_compile_lookup(self.model, k, v) for k, v in lookups.items()]
        sql = " AND ".join(w.sql for w in inner)
        params = tuple(p for w in inner for p in w.params)
        return replace(self, _where=(*self._where, Where(f"NOT ({sql})", params)), _cache=None)

    def order_by(self, *names: str) -> QuerySet[M]:
        return replace(self, _order=names, _cache=None)

    @overload
    def __getitem__(self, k: int) -> M: ...
    @overload
    def __getitem__(self, k: slice) -> QuerySet[M]: ...
    def __getitem__(self, k: int | slice) -> M | QuerySet[M]:
        if isinstance(k, int):
            if self._cache is not None:
                return self._cache[k]
            rows = list(replace(self, _limit=1, _offset=self._offset + k))
            if not rows:
                raise IndexError(k)
            return rows[0]
        start = k.start or 0
        limit = None if k.stop is None else k.stop - start
        return replace(self, _offset=self._offset + start, _limit=limit, _cache=None)

    # --- SQL --------------------------------------------------------------------------------
    def _sql(self, select: str = "*") -> tuple[str, tuple[Any, ...]]:
        sql = f'SELECT {select} FROM "{self.model._meta.table}"'
        params: list[Any] = []
        if self._where:
            sql += " WHERE " + " AND ".join(w.sql for w in self._where)
            params += [p for w in self._where for p in w.params]
        if self._order and select == "*":
            cols = [
                f'"{n.lstrip("-")}" {"DESC" if n.startswith("-") else "ASC"}' for n in self._order
            ]
            sql += " ORDER BY " + ", ".join(cols)
        if self._limit is not None or self._offset:
            sql += f" LIMIT {self._limit if self._limit is not None else -1} OFFSET {self._offset}"
        return sql, tuple(params)

    # --- evaluation ---------------------------------------------------------------------------
    def _fetch(self) -> list[M]:
        if self._cache is None:
            sql, params = self._sql()
            rows = Database.get_default().execute(sql, params).fetchall()
            object.__setattr__(self, "_cache", [self.model._from_row(r) for r in rows])
        assert self._cache is not None
        return self._cache

    def __iter__(self) -> Iterator[M]:
        return iter(self._fetch())

    def __len__(self) -> int:
        return len(self._fetch())

    def __bool__(self) -> bool:
        return bool(self._fetch())

    def __repr__(self) -> str:
        return f"<QuerySet {self._fetch()[:20]!r}>"

    def count(self) -> int:
        sql, params = self._sql("COUNT(*)")
        row = Database.get_default().execute(sql, params).fetchone()
        return int(row[0])

    def exists(self) -> bool:
        return self[:1].count() > 0

    def first(self) -> M | None:
        rows = list(self[:1])
        return rows[0] if rows else None

    def get(self, **lookups: Any) -> M:
        rows = list(self.filter(**lookups)[:2]) if lookups else list(self[:2])
        if not rows:
            raise self.model.DoesNotExist(f"{self.model.__name__} matching query does not exist")
        if len(rows) > 1:
            raise MultipleObjectsReturned(f"get() returned more than one {self.model.__name__}")
        return rows[0]

    def values(self, *names: str) -> list[dict[str, Any]]:
        names = names or tuple(self.model._meta.fields)
        return [{n: getattr(obj, n) for n in names} for obj in self]

    # --- bulk writes ---------------------------------------------------------------------------
    def update(self, **values: Any) -> int:
        meta = self.model._meta
        sets, params = [], []
        for k, v in values.items():
            fld = meta.fields[k]
            sets.append(f'"{k}" = ?')
            params.append(fld.to_db(fld.validate(v)))
        where_sql, where_params = self._where_only()
        sql = f'UPDATE "{meta.table}" SET {", ".join(sets)}{where_sql}'
        db = Database.get_default()
        with db.transaction():
            cur = db.execute(sql, (*params, *where_params))
        return cur.rowcount

    def delete(self) -> int:
        where_sql, params = self._where_only()
        db = Database.get_default()
        with db.transaction():
            cur = db.execute(f'DELETE FROM "{self.model._meta.table}"{where_sql}', params)
        return cur.rowcount

    def _where_only(self) -> tuple[str, tuple[Any, ...]]:
        if not self._where:
            return "", ()
        return (
            " WHERE " + " AND ".join(w.sql for w in self._where),
            tuple(p for w in self._where for p in w.params),
        )


__all__ = ["DoesNotExist", "QuerySet"]
