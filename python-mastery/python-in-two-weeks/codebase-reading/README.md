# Codebase reading — one chunk per day

Analytical reading is what separates "writes Python" from "writes Pythonic Python."
Each day, 45 minutes: clone or open the repo, read the named section, answer the prompts in `journal.md`.
Don't skim the whole file. Read the named functions closely enough to explain them to someone.

Repos (clone once):
```bash
git clone --depth 1 https://github.com/Textualize/rich
git clone --depth 1 https://github.com/encode/httpx
git clone --depth 1 https://github.com/fastapi/typer
git clone --depth 1 https://github.com/fastapi/fastapi
git clone --depth 1 https://github.com/psf/requests
python -c "import contextlib, dataclasses, sqlite3; print(contextlib.__file__, dataclasses.__file__, sqlite3.__file__)"   # stdlib paths
```
Paths below are as of the repos' `main` branches; if a file has moved, `grep -rn "def <name>"`.

## Day 1–2 — `rich/text.py`
Read: `class Text` → `__len__`, `__getitem__`, `__add__`, `__contains__`, and `Text.split`.
- How does `__getitem__` handle both an `int` and a `slice`? Why does slicing return a new `Text` with spans re-offset rather than a plain `str`?
- Find three list comprehensions and two generator expressions. For each, why that form and not a loop?
- Where does the class use tuple unpacking in a `for`?

## Day 3 — `dataclasses.py` (stdlib) and `rich/style.py`
Read: `dataclasses._process_class`, `_init_fn`, `field()`; then `rich/style.py` `class Style`.
- `_init_fn` builds `__init__` from a string and `exec`s it. Trace how a `default_factory` field ends up in the generated signature.
- `Style` is immutable and heavily cached. Find `__hash__`, `__eq__`, and `@lru_cache`. Why does immutability make caching safe?
- Which `Style` methods use `@property`? Which use `@classmethod` as alternate constructors?

## Day 4 — `contextlib.py` (stdlib) and `typer/main.py`
Read: `contextlib._GeneratorContextManager.__enter__`/`__exit__`; `contextmanager`; then `typer/main.py` `Typer.command`.
- In `__exit__`, why is the exception thrown *into* the generator with `self.gen.throw`? What happens to code after the `yield` when the body raised?
- `Typer.command` is a decorator factory: `@app.command()` → returns a decorator → returns the original function unchanged. Why return `f` rather than a wrapper?
- How does `wraps`/`update_wrapper` matter for CLI help text?

## Day 5 — `httpx` project layout
Read: `pyproject.toml`, `httpx/__init__.py`, `tests/conftest.py`, `tests/test_api.py`.
- What does `__init__.py` re-export, and what does `__all__` control?
- List the fixtures in `conftest.py`. Which use `yield` for teardown? Which are `scope="session"` and why?
- What does the `[tool.ruff]`/`[tool.mypy]` config enable that your template doesn't?

## Day 6–7 — `typer` and `rich` as consumers
Read: `typer/testing.py` `CliRunner`; `rich/table.py` `Table.add_row` and `Table.__rich_console__`.
- How does `CliRunner.invoke` capture stdout without a real terminal?
- `__rich_console__` is a *protocol* rich defines. Find where `Console.print` checks for it. How is this like a TS interface with duck typing?

## Day 8 — `httpx/_client.py`
Read: `class BaseClient`, `class Client.send`, `class AsyncClient.send`, `_send_single_request` in both.
- The sync and async clients share almost all logic via `BaseClient`. Find the exact lines that differ. What's the pattern for avoiding two copies of everything?
- Where is the connection pool released — which context manager?
- Search for `Semaphore` or concurrency limits in `httpx/_transports/default.py`. How are limits configured?

## Day 9 — `requests/exceptions.py` and `rich/logging.py`
Read: all of `requests/exceptions.py` (short); `rich/logging.py` `RichHandler.emit`.
- Draw the exception tree. Why do some classes inherit from both `RequestException` and a builtin like `ValueError`?
- In `RichHandler.emit`, how does it get the traceback from the `LogRecord`? What does `logging.Handler.emit` promise the subclass?

## Day 10 — `fastapi/routing.py` and `fastapi/dependencies/utils.py`
Read: `APIRoute.__init__`; `get_request_handler`; `get_dependant` and `solve_dependencies`.
- How does FastAPI decide a parameter is path vs query vs body? Find the exact function.
- `Depends` resolution is a recursive walk. Where is the cache for a dependency reused within one request?
- Find where `yield`-based dependencies get their teardown run.

## Day 11 — `sqlite3/__init__.py` + `polars` API surface
Read: stdlib `sqlite3` package (`__init__.py`, `dbapi2.py`) — note how thin it is over the C module; then polars `py-polars/polars/dataframe/frame.py` `DataFrame.filter` and `with_columns`, and `expr/expr.py` `Expr.__add__`.
- `Connection.__enter__`/`__exit__` are implemented in C. Read the docs docstring: what does `__exit__` do and not do?
- In polars, every operator on `Expr` builds a new lazy expression. Find `__add__` and trace to `wrap_expr`. How is this like a query builder?

## Day 12–14 — your own reference implementation
Read `docpipe/` against yours. For every place they differ, decide: which is more idiomatic, and why? Write the answer in `NOTES.md`.
