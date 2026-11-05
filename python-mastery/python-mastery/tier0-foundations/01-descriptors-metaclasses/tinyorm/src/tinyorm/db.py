"""Connection holder with a query log (used by tests to prove laziness)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from tinyorm.models import Model


class Database:
    default: ClassVar[Database | None] = None

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.log: list[tuple[str, tuple[Any, ...]]] = []
        Database.default = self

    @classmethod
    def get_default(cls) -> Database:
        if cls.default is None:
            raise RuntimeError("no Database configured; construct one first")
        return cls.default

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        self.log.append((sql, params))
        return self.conn.execute(sql, params)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
        except Exception:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    def create_tables(self, *models: type[Model]) -> None:
        for m in models:
            cols = ", ".join(f.column_sql() for f in m._meta.fields.values())
            self.execute(f'CREATE TABLE IF NOT EXISTS "{m._meta.table}" ({cols})')
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
        if Database.default is self:
            Database.default = None
