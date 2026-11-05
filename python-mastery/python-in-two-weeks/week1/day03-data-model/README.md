# Day 3: The data model — dicts, dataclasses, dunders, typing

## Objectives
- Model data with `dataclass`, `TypedDict`, `NamedTuple`, `Enum`, and know which to pick
- Make your objects behave like builtins via dunder methods
- Write type hints that carry your TS instincts over: unions, generics, `Protocol`, `Literal`

## Readings

| Source | Where | Read |
|---|---|---|
| `dataclasses` | https://docs.python.org/3/library/dataclasses.html | Through `field()`; skip `__post_init__` detail until needed |
| Data model | https://docs.python.org/3/reference/datamodel.html#special-method-names | "Basic customization" and "Emulating container types" |
| `typing` | https://docs.python.org/3/library/typing.html | `TypedDict`, `Protocol`, `Literal`, `TypeVar`/`Generic`, `Optional` vs `X \| None` |
| `enum` | https://docs.python.org/3/library/enum.html | `Enum`, `StrEnum`, `auto()` |
| mypy cheat sheet | https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html | All — it's short |
| *Fluent Python* ch. 1 "The Python Data Model" | Book | All — the best 20 pages in the book |
| *Fluent Python* ch. 5 "Data Class Builders" | Book | All |
| Real Python | "Python's Data Classes"; "Python Protocols: Leveraging Structural Subtyping" | Both |
| Source | `python -c "import dataclasses; print(dataclasses.__file__)"` | Read `_process_class` and `field` to see how the decorator generates `__init__` |

## Reading summaries

### Dicts are the universal record
Python has no "object literal." Ad-hoc records are dicts; typed records are `dataclass` or `TypedDict`. Rule: a dict when the keys are data (`{"user_42": ...}`); a dataclass when the keys are schema (`user.name`).

### The four record types
| Type | Use when | TS analogue |
|---|---|---|
| `@dataclass` | You want a real class with methods, defaults, `__eq__`, `__repr__` for free | `class` with a constructor |
| `@dataclass(frozen=True)` | Immutable value object; hashable, usable as dict key | `readonly` object |
| `TypedDict` | You're describing the shape of a plain dict (JSON in/out) | `interface` on a plain object |
| `NamedTuple` | Small immutable tuple with names; unpacks positionally | tuple type |
| `Enum` / `StrEnum` | A closed set of named values | `enum` / string union |

`dataclass` generates `__init__`, `__repr__`, `__eq__` (and `__hash__`, `__lt__` etc. with flags). `field(default_factory=list)` for mutable defaults. `slots=True` (3.10+) saves memory and blocks typos. `kw_only=True` forces keyword args.

### Dunder ("magic") methods — how operators and builtins dispatch
| You write | Python calls |
|---|---|
| `len(x)` | `x.__len__()` |
| `x[k]`, `x[k] = v`, `del x[k]` | `__getitem__`, `__setitem__`, `__delitem__` |
| `k in x` | `__contains__` (falls back to iteration) |
| `for i in x` | `__iter__` (or `__getitem__` with ints) |
| `x + y`, `x == y`, `x < y` | `__add__`, `__eq__`, `__lt__` (`__radd__` for reflected) |
| `str(x)`, `repr(x)` | `__str__` (user-facing), `__repr__` (debug; aim for valid constructor call) |
| `bool(x)` | `__bool__`, else `__len__` |
| `x()` | `__call__` |
| `with x:` | `__enter__` / `__exit__` (Day 4) |
| `hash(x)` | `__hash__` — needed for set/dict-key |

`@property` turns a method into a read-only attribute; add `@name.setter` for writes. Use it to add validation without changing the call site. Don't write Java getters.

`@classmethod` receives the class (alternate constructors: `Money.from_str("1.50 USD")`). `@staticmethod` receives nothing (namespaced helper).

### Typing — what transfers from TS and what doesn't
- Hints are **not enforced at runtime**. They're for `mypy`/`pyright` and readers. Runtime validation is Pydantic (Day 10).
- Builtin generics: `list[int]`, `dict[str, list[float]]`, `tuple[int, str]`, `tuple[int, ...]`, `set[str]`.
- Unions: `int | None` (3.10+). Avoid `Optional[X]` in new code.
- `Literal["asc", "desc"]` — string unions.
- `TypedDict` for JSON-shaped dicts; `total=False` or `NotRequired[...]` for optional keys.
- `Protocol` = structural typing = TS interfaces. Any class with matching methods satisfies it, no `implements` needed. This is the closest thing to how TS actually works; reach for it over ABCs.
- Generics: `def first[T](xs: list[T]) -> T` (3.12 syntax) or `T = TypeVar("T")` older style.
- `Callable[[int, str], bool]` for function types. `Iterable[T]` / `Sequence[T]` / `Mapping[K, V]` for parameters (accept the broadest thing), concrete `list[T]` for returns.
- `Any` is `any`. `object` is `unknown`. `cast()` is `as`. `TYPE_CHECKING` guards import-only-for-types.
- No narrowing on `if "k" in d` for TypedDicts the way TS narrows; use `.get()` or `NotRequired`.

### Comparison with TS classes
- No access modifiers. `_x` is "internal," `__x` name-mangles (avoid).
- No overloading by signature; use `@overload` stubs from `typing` for the checker, one real implementation.
- No interfaces; use `Protocol` or `abc.ABC` + `@abstractmethod`.
- `self` is explicit. `__init__` is the constructor (not `constructor`, not `__new__`).
- Inheritance: `class B(A):`, `super().__init__()`. Multiple inheritance exists; MRO is C3 linearization — avoid needing to know.

## Copy
`copy/01_records.py` → `copy/02_dunders.py` → `copy/03_typing.py`. Run `mypy --strict` on each.

## Analytical reading
`codebase-reading/README.md`, Day 3 (`dataclasses.py` source; `rich/style.py` for a frozen value class).

## Build task (90 min)
Model a small inventory: `Product` (frozen dataclass: sku, name, price as `Decimal`), `Category` (StrEnum), `Inventory` class with `__len__`, `__getitem__` by sku, `__contains__`, `__iter__`, `add(product, qty)`, `total_value() -> Decimal`, and a `restock_report() -> list[LowStock]` where `LowStock` is a `NamedTuple`. Write tests with pytest. Pass `mypy --strict`.
