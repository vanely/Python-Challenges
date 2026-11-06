# Step 3 — The ingestion pipeline

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/test_dp_03_pipeline.py`

## What you'll have at the end

`util.py` (hashing and a timing decorator) and `pipeline.py`, which:
- ingests a directory tree of PDFs **idempotently**: unchanged files are skipped by content hash, and `--force` overrides that;
- isolates failures per file, so one corrupt or weird PDF never stops a batch of 500;
- returns an `IngestReport` with counts and elapsed time.

## Concepts

### Idempotency by content hash

Running `docpipe ingest` twice should do the work once. There are two ways to decide that a file is unchanged:

| Signal | Cost | Fails when |
|---|---|---|
| modification time + size | one `stat()` | a copy or `git checkout` changes mtime with identical content (spurious re-ingest), or a tool rewrites a file preserving mtime (missed change) |
| SHA-256 of the bytes | read the whole file | effectively never |

PDFs here are small and extraction costs far more than hashing, so hash. `hashlib.file_digest(f, "sha256")` (3.11+) reads in blocks, so a 2 GB file doesn't need 2 GB of memory.

### Path keys must be canonical

The store keys documents by path. `docs/a.pdf`, `./docs/a.pdf` and `C:\work\docs\a.pdf` must be the same key, or the "skip unchanged" logic silently re-ingests duplicates. `path.resolve()` makes it absolute and resolves `..` and symlinks. `.as_posix()` uses forward slashes, so a database built on Windows has the same keys as one built in WSL or CI.

### Error boundaries: where to catch `Exception`

"Never catch `Exception`" is a good default with one important exception: the **boundary of a unit of work in a batch**. Here the unit is one file. Inside it, anything can go wrong: pypdf has bugs, a PDF can contain a font table that makes it raise `KeyError` on page 47, the disk can fill. None of that should cost you the other 499 files.

So the loop has two handlers:

```python
except ExtractError as e:     # expected, already explained: "not a PDF", "encrypted"
    log.error("skipping %s", e)       # one line, no traceback; e already names the file
except Exception:             # unexpected: a bug somewhere, yours or pypdf's
    log.exception("failed: %s", path)                # ERROR level + full traceback
```

Narrow first, broad second. `log.exception` is `log.error` plus the current traceback, and it's only meaningful inside an `except` block. Without the traceback, an unexpected error is undebuggable: you'd know *that* `boom.pdf` failed but not where.

Never catch `BaseException` here: `KeyboardInterrupt` should still stop the run.

### Failure must not corrupt the previous version

Combine step 2's atomic `replace_document` with the order of operations here. **Extract everything first, then replace in one transaction.** If extraction dies on page 2 of a re-ingest, `replace_document` is never called and the old version stays searchable. The checkpoint tests exactly that scenario.

### A typed timing decorator

```python
def timed[**Q, S](fn: Callable[Q, S]) -> Callable[Q, S]:
```

This is PEP 695 syntax (3.12+). `**Q` is a `ParamSpec`, which captures the *whole* parameter list, including keyword-only `force`. The decorated `ingest_file` keeps its exact signature for mypy and your editor. `try/finally` logs the time even when the function raises.

## Build

### 1. `src/docpipe/util.py`

```python
"""Small cross-cutting helpers: timing decorator, hashing."""

from __future__ import annotations

import functools
import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)


def timed[**Q, S](fn: Callable[Q, S]) -> Callable[Q, S]:
    @functools.wraps(fn)
    def wrapper(*args: Q.args, **kwargs: Q.kwargs) -> S:
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            log.debug("%s took %.3fs", fn.__qualname__, time.perf_counter() - t0)

    return wrapper


def sha256_of(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
```

- `time.perf_counter()`, not `time.time()`: it's monotonic (immune to clock adjustments) and high-resolution. Use it for durations, and `time.time()` only for wall-clock timestamps.
- `log.debug` with `%s` arguments, not an f-string: if DEBUG is off, the string is never formatted.

### 2. `src/docpipe/pipeline.py`, minus `ingest_dir`

```python
"""Ingestion: walk a directory, skip unchanged files, extract -> chunk -> store."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from pypdf import PdfReader

from docpipe.extract import ExtractError, iter_chunks
from docpipe.models import IngestReport
from docpipe.store import Store
from docpipe.util import sha256_of, timed

log = logging.getLogger(__name__)


@timed
def ingest_file(path: Path, store: Store, *, force: bool = False) -> int:
    """Returns number of chunks stored, or -1 if skipped as unchanged."""
    key = path.resolve().as_posix()  # forward slashes on every OS
    digest = sha256_of(path)
    existing = store.find_by_path(key)
    if existing and existing.sha256 == digest and not force:
        return -1
    chunks = list(iter_chunks(path))  # materialise: we need the count + one txn
    pages = len(PdfReader(path).pages)  # cheap: no text extraction; iter_chunks proved it opens
    store.replace_document(key, digest, pages, chunks)
    return len(chunks)
```

- `from docpipe.extract import iter_chunks`, **not** `iter_pages`. The checkpoint replaces `docpipe.extract.iter_pages` with a version that fails on page 2. `iter_chunks` looks up `iter_pages` in its module's globals at call time, so it sees the replacement. If you'd written `from docpipe.extract import iter_pages` here and called it directly, you'd hold a reference to the original and the patch would miss.
- `list(...)` before `replace_document`: if extraction fails, it fails *before* the store is touched. Holding one document's chunks in memory is fine. Holding the whole corpus wouldn't be, and we don't.
- `-1` as a sentinel for "skipped" is a pragmatic choice. A richer design returns an enum or a small result object. What would you change, and what would that cost the callers?
- `*` makes `force` keyword-only: `ingest_file(p, store, True)` is a `TypeError`, so nobody passes a mystery boolean.

### 3. Your turn: `ingest_dir`

```python
def ingest_dir(directory: Path, store: Store, *, force: bool = False) -> IngestReport:
```

Spec:
- Process every `*.pdf` under `directory`, **recursively**, in **sorted** order (deterministic logs and ids). Ignore other files.
- For each file, call `ingest_file`. A return of `-1` counts as `skipped` (log at INFO "unchanged: name"). Otherwise count `ingested` and add to `chunks` (log at INFO "ingested: name (N chunks)").
- `ExtractError` counts as `failed`, logged with `log.error` and **no** traceback. Its message already contains the path, so don't add it a second time.
- Any other `Exception` counts as `failed`, logged with `log.exception`, including the path.
- Set `report.seconds` to the elapsed time with `perf_counter`.

<details><summary>Hint: recursion and order</summary>

`Path.rglob("*.pdf")` walks subdirectories. Wrap it in `sorted(...)`. `Path` objects are orderable: they compare component by component, case-insensitively on Windows.
</details>

<details><summary>Hint: why does the checkpoint check `rec.exc_info`?</summary>

`log.exception` attaches `sys.exc_info()` to the log record, and that's what makes the traceback appear in the output. `log.error(str(e))` doesn't. The test checks that you kept the traceback for unexpected failures.
</details>

### 4. Try it

```bash
uv run python
>>> import logging; logging.basicConfig(level=logging.DEBUG)
>>> from pathlib import Path; from docpipe.store import Store; from docpipe.pipeline import ingest_dir
>>> s = Store("try.db")
>>> ingest_dir(Path("../samples"), s)
>>> ingest_dir(Path("../samples"), s)              # all skipped
>>> ingest_dir(Path("../samples"), s, force=True)
>>> s.search("phonics")[:2]
```

Copy a text file into `../samples/` renamed as `broken.pdf` and run it again: one `failed`, no traceback, and the rest are fine. Delete it afterwards, and delete `try.db*`.

## Checkpoint

```bash
uv run pytest ../checkpoints/test_dp_03_pipeline.py
uv run mypy src && uv run ruff check .
```

This project's ruff rules don't include `BLE` (blind except). If you add it later, it will flag this `except Exception`. This is the one place a blind except is correct, so silence it on that line with `# noqa: BLE001` and a reason.

## Pitfalls

- **Relative or backslash path keys.** The same file ingested from two working directories becomes two documents.
- **`log.error(e)` for unexpected errors.** You lose the traceback, which is the only thing that would let you fix it.
- **One `try` around the whole loop.** The first failure ends the batch.
- **Calling `replace_document` with a generator that's still extracting.** It's atomic either way (step 2), but you'd lose the chunk count and hold a write transaction open for the whole extraction.
- **mtime-based skipping.** It's fast and wrong in the cases you'll hit (fresh clones, copied folders).

## Explain it back

1. Why hash the content instead of checking the modification time?
2. When is `except Exception` the right call, and why are there two handlers here instead of one?
3. What does `log.exception` add over `log.error`, and why must it be called inside `except`?
4. Walk through what the database contains after a re-ingest that dies on page 2. Which two design decisions guarantee that?
5. Why does patching `docpipe.extract.iter_pages` affect `iter_chunks`, but wouldn't affect a module that did `from docpipe.extract import iter_pages`?
6. What does `**Q` capture that `*args: Any` wouldn't?
