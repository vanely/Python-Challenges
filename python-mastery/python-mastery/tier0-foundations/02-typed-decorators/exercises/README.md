# Exercises — 8 typed decorators

Implement each in `decorators.py`. Two gates:
1. `pytest test_decorators.py` — runtime behaviour
2. `mypy --strict --disable-error-code=empty-body decorators.py typecheck.py` — the `typecheck.py` file contains `reveal_type` and deliberate-error lines with `# type: ignore[...]` comments; if your types are wrong, mypy reports *unused* ignores or new errors. Zero output = pass.

| # | Decorator | Typing rung |
|---|---|---|
| 1 | `@once` — call at most once, cache result | same-signature wrapper |
| 2 | `@debounce(seconds)` — ignore calls within N seconds of the last accepted one; returns `R \| None` | parameterised, return changes |
| 3 | `@with_lock(lock)` — hold a `threading.Lock` around the call | parameterised, same-signature |
| 4 | `@inject_logger` — decorated fn signature is `(logger, *args)`; caller doesn't pass the logger | `Concatenate` |
| 5 | `@ensure_async` — accepts sync *or* async functions, always returns a coroutine function | `overload` on the decorator |
| 6 | `@count` — class-based; exposes `.calls: int`; preserves signature | generic class with `__call__` |
| 7 | `@validate_types` — check runtime args against annotations via `inspect.signature`/`get_type_hints`; raise `TypeError` | same-signature; uses `typing.get_type_hints` |
| 8 | `@lazy` — descriptor: computes once per instance; `Cls.attr` returns the descriptor | descriptor with `__get__` overloads |
