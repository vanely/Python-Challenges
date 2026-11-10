# 0.2 — Typing for real: decorators, generics, protocols, overloads

You've written Python without a type checker enforcing anything. This module makes `mypy --strict` a tool you drive rather than fight, using decorators as the forcing function — they're where typing gets hard.

## Objectives
- Type any decorator (plain, parameterised, class-based, method-aware) so the wrapped signature survives
- Use `ParamSpec`, `Concatenate`, `TypeVar` bounds/constraints/variance, `Protocol`, `overload`, `TypeGuard`/`TypeIs`, `Self`, `TypeVarTuple`, PEP 695 syntax
- Read typeshed and library `.pyi` stubs fluently; know when `Any` is honest and when it's laziness

## Readings

| Source | Where | Read |
|---|---|---|
| typing module docs | https://docs.python.org/3/library/typing.html | Everything under "Special forms" and "Building generic types" |
| mypy docs | https://mypy.readthedocs.io/en/stable/generics.html | All of "Generics" incl. variance, `ParamSpec`, generic protocols |
| mypy: protocols | https://mypy.readthedocs.io/en/stable/protocols.html | All; note the predefined protocols list |
| mypy: type narrowing | https://mypy.readthedocs.io/en/stable/type_narrowing.html | `TypeGuard`, `TypeIs`, `assert_never` |
| PEP 612 | https://peps.python.org/pep-0612/ | `ParamSpec` + `Concatenate` — the decorator PEP. Read the motivating examples. |
| PEP 544 | https://peps.python.org/pep-0544/ | Protocols. Skim rationale, read "Protocol members", "Explicitly declaring implementation" |
| PEP 695 | https://peps.python.org/pep-0695/ | 3.12 type-parameter syntax + variance inference |
| PEP 692 / 646 / 698 / 742 | peps.python.org | `TypedDict **kwargs`, `TypeVarTuple`, `@override`, `TypeIs` — skim each |
| Typing spec | https://typing.readthedocs.io/en/latest/spec/ | Bookmark; read "Generics" and "Callables" |
| typeshed | https://github.com/python/typeshed → `stdlib/functools.pyi`, `stdlib/contextlib.pyi`, `stdlib/builtins.pyi` (`property`, `classmethod`) | See how the stdlib types its own decorators |
| Library stubs | `django-stubs`: `django-stubs/db/models/manager.pyi`, `fields/__init__.pyi` — how `Field.__get__` overloads produce `int` vs `Field` | Compare with your `tinyorm` field |
| Fluent Python ch. 8 "Type Hints in Functions" and ch. 15 "More About Type Hints" | Book | All of both |

## Reading summaries

### The decorator typing ladder
1. **Passthrough** (`fn -> fn`): `def deco[F: Callable[..., Any]](fn: F) -> F`. Cheapest; use when you return the *same* function (registration, marking).
2. **Wrapper, same signature**: `def deco[**P, R](fn: Callable[P, R]) -> Callable[P, R]` with `wrapper(*args: P.args, **kwargs: P.kwargs) -> R`. This is the 90% case.
3. **Wrapper that changes the return**: `Callable[P, R] -> Callable[P, Awaitable[R]]` or `-> Callable[P, R | None]`.
4. **Wrapper that adds/removes a leading arg**: `Concatenate[Request, P]` — e.g. a view decorator that injects `request`.
5. **Parameterised** (`@retry(times=3)`): a function returning a decorator; type the outer as `-> Callable[[Callable[P, R]], Callable[P, R]]`.
6. **Class-based** with `__call__`: make the class generic in `P, R` and store the callable; `functools.update_wrapper(self, fn)`.
7. **Method decorators** need to accept `self`: `P` already includes it — `Concatenate[Any, P]` only if you must name it.
8. **Decorators returning a descriptor** (like `cached_property`): overloads on `__get__` with `obj: None` vs `obj: object`.

### Variance, in one paragraph
`list[Dog]` is **not** a `list[Animal]` (invariant: you could append a Cat). `Sequence[Dog]` **is** a `Sequence[Animal]` (covariant: read-only). `Callable[[Animal], None]` **is** a `Callable[[Dog], None]` (contravariant in args). Accept `Sequence`/`Iterable`/`Mapping` in parameters, return concrete `list`/`dict`. PEP 695 infers variance for you; old-style `TypeVar(covariant=True)` must be declared.

### Protocol vs ABC
Protocol = structural (TS interface). ABC = nominal + can carry implementation + `register()`. Use Protocol for "accepts anything with `.read()`"; use ABC when you own the hierarchy. `@runtime_checkable` enables `isinstance` but only checks method *presence*, not signatures.

### `overload`
Declare N stub signatures with `...` bodies, then one real implementation whose type is the union. The checker picks by argument types; the implementation must handle all. Use for: `__get__` on descriptors, functions whose return type depends on a flag (`open(..., "rb") -> BinaryIO`), and to *avoid* `T | None` returns.

### Narrowing
`isinstance`, `is None`, `in` on literals, `match`, `assert`, and user-defined `TypeGuard[T]` (narrows only the positive branch) / `TypeIs[T]` (3.13, narrows both). `assert_never(x)` in the `else` of an exhaustive `match` makes the checker enforce exhaustiveness — use it on every enum/union dispatch.

### `Self`, `TypeVarTuple`, `TypedDict` kwargs
`-> Self` for fluent builders and `classmethod` constructors (replaces the `T = TypeVar("T", bound="Cls")` dance). `*Ts` for variadic generics (`tuple[*Ts]`, shape-typed arrays). `**kwargs: Unpack[Opts]` types keyword args with a `TypedDict`.

### When `Any` is honest
JSON, `**kwargs` passthrough to a third-party API, dynamic plugins. Prefer `object` (forces narrowing) when you *don't* need attribute access. Use `cast()` sparingly and always with a comment saying why it's safe. `# type: ignore[code]` always with the code and, ideally, a link to the upstream issue.

## Copy
`copy/01_decorator_ladder.py` — all eight rungs, each `mypy --strict` clean, with `reveal_type` checks you can run.
`copy/02_generics_protocols.py` — variance demos (with the errors mypy produces, as comments), Protocol vs ABC, `overload`, narrowing, `Self`, `TypeVarTuple`.

## Exercises
`exercises/` — 8 decorators with tests and a mypy target. `reference/solutions/` after those tests pass, not before.

## Analysis prompts
1. In typeshed's `functools.pyi`, how is `lru_cache` typed? Why does it return `_lru_cache_wrapper[T]` rather than `Callable[P, T]`? What's lost?
2. `contextlib.pyi`: `contextmanager` is typed `Callable[_P, Iterator[_T_co]] -> Callable[_P, _GeneratorContextManager[_T_co]]`. Why must the yield type be covariant?
3. `django-stubs` `Field.__get__` has three overloads. Read them and explain how `article.title` becomes `str` while `Article.title` becomes `Field`. Then explain the `_pyi_private_set_type` trick.
4. Run `mypy --strict` on any real module of yours from work. Categorise every error: real bug / missing annotation / checker limitation. Fix the first two categories.

## Build: `typed_utils`
Take the decorators from `exercises/` plus your Day-4-style `retry`/`timed`, add `rate_limit(calls, per)`, `memoize` with a typed cache key, `deprecated(reason)` emitting `DeprecationWarning`, and `validate_args` using `inspect.signature` + runtime type checks against annotations. Package it (Tier 0.5 layout), 100% typed, `py.typed` marker, tested with `pytest` **and** with mypy's own test harness (`pytest-mypy-plugins` or plain `reveal_type` assertions). This becomes a dependency of Tier 3/4 projects.
