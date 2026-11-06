# Day 9: Errors, logging, pathlib, subprocess, json/csv

The "glue" day. Everything here is stdlib and you'll use it in every script you ever write.

## Objectives
- Design exception hierarchies and handle errors the Python way (EAFP)
- Configure `logging` once and use it everywhere
- Do file, path, process, and JSON/CSV work without reaching for a third-party package

## Readings

| Source | Where | Read |
|---|---|---|
| Errors tutorial | https://docs.python.org/3/tutorial/errors.html | All, incl. `raise from`, `else`, exception groups |
| Built-in exceptions | https://docs.python.org/3/library/exceptions.html#exception-hierarchy | The hierarchy tree — memorise the top 15 |
| logging HOWTO | https://docs.python.org/3/howto/logging.html | Basic + "Advanced Logging Tutorial" up to handlers |
| pathlib | https://docs.python.org/3/library/pathlib.html | All of "Basic use" and "Methods" |
| subprocess | https://docs.python.org/3/library/subprocess.html#subprocess.run | `run()` and `CompletedProcess` only |
| json | https://docs.python.org/3/library/json.html | `default=`, `object_hook=`, `indent` |
| csv | https://docs.python.org/3/library/csv.html | `DictReader`/`DictWriter` |
| `datetime` | https://docs.python.org/3/library/datetime.html | `datetime`, `timedelta`, `fromisoformat`, timezone-aware vs naive |
| *Fluent Python* ch. 18 "with, match, and else Blocks" | Book | `else` clauses |
| Source | `requests/exceptions.py` (https://github.com/psf/requests) | How a good library structures its exception tree |
| Real Python | "Python Exceptions: An Introduction"; "Logging in Python"; "Python's pathlib Module" | All |

## Reading summaries

### Exceptions
- **EAFP**: "Easier to Ask Forgiveness than Permission." `try: d[k] except KeyError:` beats `if k in d:`. Exceptions are cheap and idiomatic for control flow around *expected* failures (missing file, bad parse).
- `try / except X as e / else / finally`. `else` runs only if no exception — put the "success path" there so `except` doesn't accidentally catch it.
- Catch the **narrowest** class. Bare `except:` catches `KeyboardInterrupt`; `except Exception:` is the widest you should ever write, and only at boundaries (top of a CLI, a request handler).
- Chain: `raise AppError("ctx") from e` preserves the cause. `from None` suppresses it.
- Define a hierarchy: one base `class AppError(Exception)`, subclasses per category. Callers catch the base. Put useful fields on them (`self.path`, `self.status`).
- Hierarchy to know: `LookupError` → `KeyError`, `IndexError`. `ValueError` (right type, bad value) vs `TypeError` (wrong type). `OSError` → `FileNotFoundError`, `PermissionError`. `RuntimeError`, `NotImplementedError`, `StopIteration`.
- `ExceptionGroup` + `except*` (3.11) for concurrent failures (TaskGroup raises these).
- `assert` is for invariants during development; it's stripped with `-O`. Never for input validation.

### logging
- Per module: `log = logging.getLogger(__name__)`. Never `print` in library code.
- Configure **once**, at the entry point: `logging.basicConfig(level=..., format=...)` or `dictConfig`. Libraries never configure.
- Levels: DEBUG < INFO < WARNING < ERROR < CRITICAL. Default is WARNING, so your `log.info` is silent until you configure.
- Lazy formatting: `log.info("user %s logged in", uid)` not f-strings — args are formatted only if the level is enabled.
- `log.exception("msg")` inside `except` includes the traceback.
- Handlers route (stderr, file, rotating file), formatters shape, filters drop. Structured/JSON logging: `python-json-logger` or `structlog` when you need it.

### pathlib
- `Path` objects, `/` joins: `Path.home() / "data" / f"{name}.json"`.
- `.read_text() / .write_text() / .read_bytes()`, `.open()` as a context manager.
- `.exists() / .is_file() / .is_dir()`, `.mkdir(parents=True, exist_ok=True)`, `.unlink(missing_ok=True)`.
- `.glob("**/*.py")` and `.rglob`, `.iterdir()`.
- `.name / .stem / .suffix / .parent / .parts`, `.with_suffix(".bak")`, `.resolve()`.
- Always `encoding="utf-8"` explicitly on text I/O. Windows defaults differ.

### subprocess
- `subprocess.run(["git", "status"], capture_output=True, text=True, check=True)` → `CompletedProcess` with `.stdout`, `.returncode`. `check=True` raises `CalledProcessError` on non-zero.
- Pass a **list**, never a shell string (injection + quoting bugs). `shell=True` only for pipes you truly need.
- `timeout=` kills hung processes. `cwd=`, `env=` for context.

### json / csv / datetime
- `json.dumps(obj, indent=2, default=fn)` — `default` handles non-serialisable types (datetime, Decimal, dataclasses via `asdict`). `json.loads` returns plain dicts/lists — validate with Pydantic (Day 10) if it matters.
- `csv.DictReader(f)` yields `dict[str, str]` per row; `DictWriter(f, fieldnames=[...])` + `.writeheader()`. Open with `newline=""`.
- `datetime.now(tz=timezone.utc)` — always timezone-aware. `fromisoformat` parses ISO 8601. `timedelta` for arithmetic. `strftime`/`strptime` for custom formats. `zoneinfo.ZoneInfo("America/New_York")` for named zones. On Windows, also install `tzdata` (`uv add tzdata`); there's no system time zone database.

## Copy
`copy/01_exceptions.py` → `copy/02_logging.py` → `copy/03_paths_files.py` → `copy/04_subprocess_json_csv.py`

## Analytical reading
`codebase-reading/README.md`, Day 9 (`requests/exceptions.py`; `rich/logging.py`).

## Build task (90 min)
`logtriage.py`: walk a directory of `*.log` files (use `rglob`), parse lines shaped like `2026-09-11T10:00:00Z ERROR module: message`, and write `summary.csv` (module, level, count) and `errors.json` (last 10 errors per module, newest first). Define `ParseError(AppError)` with `path` and `lineno` fields; log a warning and skip bad lines; log an exception and exit non-zero on unreadable files. Configure logging so `--verbose` enables DEBUG. Run `git log --oneline -5` via `subprocess` and include the commit hash in `errors.json` metadata if in a repo.
