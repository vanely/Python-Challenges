"""Fields are data descriptors. The field object is shared; values live on instances."""

from __future__ import annotations

from typing import Any, overload

from tinyorm.exceptions import ValidationError

_MISSING = object()


class Field:
    sql_type = "TEXT"
    py_type: type | tuple[type, ...] = object

    def __init__(
        self,
        *,
        default: Any = _MISSING,
        null: bool = False,
        primary_key: bool = False,
        unique: bool = False,
    ) -> None:
        self.default = default
        self.null = null
        self.primary_key = primary_key
        self.unique = unique
        self.name = ""  # set by __set_name__
        self.attr = ""  # instance storage key

    # --- descriptor protocol ---------------------------------------------------------------
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.attr = f"_f_{name}"

    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> Field: ...
    @overload
    def __get__(self, obj: object, objtype: type | None = None) -> Any: ...
    def __get__(self, obj: object | None, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        try:
            return obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError(self.name) from None

    def __set__(self, obj: object, value: Any) -> None:
        obj.__dict__[self.attr] = self.validate(value)

    # --- validation + conversion ------------------------------------------------------------
    def validate(self, value: Any) -> Any:
        if value is None:
            if self.null or self.primary_key:
                return None
            raise ValidationError(f"{self.name}: null not allowed")
        if self.py_type is not object and not isinstance(value, self.py_type):
            raise ValidationError(
                f"{self.name}: expected {self._type_name()}, got {type(value).__name__}"
            )
        return value

    def _type_name(self) -> str:
        t = self.py_type
        return "/".join(x.__name__ for x in t) if isinstance(t, tuple) else t.__name__

    def get_default(self) -> Any:
        if self.default is _MISSING:
            return None
        return self.default() if callable(self.default) else self.default

    def to_db(self, value: Any) -> Any:
        return value

    def from_db(self, value: Any) -> Any:
        return value

    def column_sql(self) -> str:
        parts = [f'"{self.name}"', self.sql_type]
        if self.primary_key:
            parts.append("PRIMARY KEY")
        elif not self.null:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r})"


class IntegerField(Field):
    sql_type = "INTEGER"
    py_type = int

    def validate(self, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValidationError(f"{self.name}: bool is not an int here")
        return super().validate(value)


class FloatField(Field):
    sql_type = "REAL"
    py_type = (int, float)

    def validate(self, value: Any) -> Any:
        v = super().validate(value)
        return float(v) if v is not None else None


class TextField(Field):
    sql_type = "TEXT"
    py_type = str

    def __init__(self, *, max_length: int | None = None, **kw: Any) -> None:
        super().__init__(**kw)
        self.max_length = max_length

    def validate(self, value: Any) -> Any:
        v = super().validate(value)
        if v is not None and self.max_length is not None and len(v) > self.max_length:
            raise ValidationError(f"{self.name}: longer than {self.max_length}")
        return v
