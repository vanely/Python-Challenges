# Step 1 — Models, streaming extraction, and chunking

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/test_dp_01_extract.py`

## What you'll have at the end

- The package scaffold and every model the project uses.
- `extract.py`: `iter_pages` (one page at a time, with no PDF ever fully in memory as text), `chunk_text` (paragraph-aware, size-bounded, overlapping chunks) and `iter_chunks` (the two composed).

## Concepts

### Why chunk at all?

Search quality depends on the unit you index. Index whole documents, and a 200-page manual matches every query and the "hit" tells you nothing. Index sentences, and you lose context. Chunks of a few paragraphs (~800 characters) are the usual compromise: specific enough to rank, big enough to read. This is the same preprocessing an LLM retrieval pipeline ("RAG") does before embedding text.

Two rules make chunks good:
- **Respect structure.** Break at paragraph boundaries when possible, so a chunk doesn't start mid-sentence.
- **Overlap.** Start each chunk with the tail of the previous one. A phrase that straddles a boundary is then still found whole in one chunk.

### The algorithm you'll implement

Greedy packing: split the text into paragraphs (blank-line separated). Keep a buffer:
1. If the buffer plus `"\n\n"` plus the next paragraph fits in `size`, append it.
2. Otherwise, emit the buffer and start a new one with the paragraph. If the last `overlap` characters of the emitted buffer *also* fit in front of it, start with those.
3. A paragraph longer than `size` on its own can't be packed. First emit whatever is buffered, **don't drop it**. Then cut the paragraph into windows of `size` characters that advance by `size - overlap`.

The window arithmetic deserves care. For a 550-character paragraph with `size=300, overlap=50`, the step is 250, and windows start at 0 and 250: `[0:300]` and `[250:550]`, which covers everything. A naive `range(0, 550, 250)` also starts a window at 500, giving `[500:550]`: 50 characters that are entirely inside the previous window, a redundant chunk that duplicates search hits. The fix is to stop starting windows at `len(para) - overlap`: `range(0, len(para) - overlap, size - overlap)`. Convince yourself that the last window still reaches the end. (Hint: the last start `i` satisfies `i >= len - overlap - step`.)

### Generators for streaming

`iter_pages` yields one `Page` at a time, and `iter_chunks` consumes it lazily. A 2,000-page PDF never has more than one page's text in memory, and a consumer that stops early stops the extraction too. It's the same idea as fetchr's pagination, applied to a file.

### Wrapping third-party exceptions

pypdf raises many different exception types for broken files (`PdfReadError`, `ValueError`, `KeyError`, …). Callers shouldn't need to know them. Wrap them at the boundary in one exception **you** own:

```python
try:
    reader = PdfReader(path)
except Exception as e:  # pypdf raises a zoo of exception types
    raise ExtractError(path, f"cannot open PDF ({type(e).__name__}: {e})") from e
```

`raise ... from e` sets `__cause__`, so the traceback shows both: "The above exception was the direct cause of…". Without `from`, you lose the original. (With `from None`, you suppress it on purpose.)

This is one of the few places where `except Exception` is right: a narrow boundary around one third-party call, whose failure modes you can't enumerate, re-raised as a typed error with the original attached.

### Logging in a library

```python
log = logging.getLogger(__name__)      # "docpipe.extract"
log.info("%s page %d: no text (scanned?)", path.name, i)
```

- One logger per module, named after the module. Configuration (levels, format, where output goes) is the **application's** job, in the CLI's entry point (step 4). Library code never calls `logging.basicConfig`.
- Pass arguments with `%s` rather than an f-string. Formatting is skipped entirely when the level is disabled, and log aggregators can group messages by their template.

### Dataclasses inside, Pydantic at the boundary

`Page`, `Chunk` and `Document` are internal. Your code builds them from trusted data, so frozen slotted dataclasses (fast, no validation) are right. `SearchHit` and `DocumentOut` cross the HTTP boundary in step 5. FastAPI uses them to validate, serialise and document responses, so they're Pydantic `BaseModel`s. Use each tool where its strengths matter. This is the Day 10 rule applied for real.

## Build

### 1. `pyproject.toml`

```toml
[project]
name = "docpipe"
version = "0.1.0"
description = "PDF -> chunks -> SQLite FTS -> search API"
requires-python = ">=3.12"
dependencies = [
    "pypdf>=4",
    "typer>=0.12",
    "rich>=13",
    "polars>=1",
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "pydantic>=2.8",
]

[project.scripts]
docpipe = "docpipe.cli:app"

[dependency-groups]
dev = ["pytest>=8", "httpx2>=2", "ruff>=0.6", "mypy>=1.12"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
strict = true

[[tool.mypy.overrides]]
module = ["pypdf.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

`httpx2` is what FastAPI's `TestClient` uses under the hood (step 5). Then run `uv sync`.

Replace the generated `src/docpipe/__init__.py` with a one-line docstring. Its `main()` is dead now that the script points at `docpipe.cli:app`. Then `mkdir tests` for your own tests (`uv init` doesn't create it).

### 2. `src/docpipe/models.py`

```python
"""Internal records are dataclasses; API-boundary records are Pydantic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class Page:
    number: int  # 1-based
    text: str


@dataclass(frozen=True, slots=True)
class Chunk:
    page_no: int
    index: int  # position within the document
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True, slots=True)
class Document:
    id: int
    path: str
    sha256: str
    pages: int
    ingested_at: datetime


@dataclass(slots=True)
class IngestReport:
    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    chunks: int = 0
    seconds: float = 0.0


class SearchHit(BaseModel):
    document_id: int
    path: str
    page_no: int
    chunk_index: int
    score: float = Field(description="Lower is better (bm25)")
    snippet: str


class DocumentOut(BaseModel):
    id: int
    path: str
    pages: int
    chunks: int
    ingested_at: datetime
```

`IngestReport` is deliberately **not** frozen: the pipeline increments its counters as it goes. `str.split()` with no argument splits on any run of whitespace, including newlines, and ignores the ends. `"a  b\nc".split()` is `["a", "b", "c"]`.

### 3. `src/docpipe/extract.py`, minus `chunk_text`

```python
"""PDF text extraction and chunking. Both are generators: nothing is held in memory."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path

from pypdf import PdfReader

from docpipe.models import Chunk, Page

log = logging.getLogger(__name__)
_PARA = re.compile(r"\n\s*\n")
_WS = re.compile(r"[ \t]+")


class ExtractError(Exception):
    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path


def iter_pages(path: Path) -> Iterator[Page]:
    try:
        reader = PdfReader(path)
    except Exception as e:  # pypdf raises a zoo of exception types
        raise ExtractError(path, f"cannot open PDF ({type(e).__name__}: {e})") from e
    for i, page in enumerate(reader.pages, start=1):
        text = _clean(page.extract_text() or "")
        if not text:
            log.info("%s page %d: no text (scanned?)", path.name, i)
        yield Page(number=i, text=text)


def _clean(text: str) -> str:
    text = _WS.sub(" ", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def iter_chunks(path: Path, size: int = 800, overlap: int = 100) -> Iterator[Chunk]:
    idx = 0
    for page in iter_pages(path):
        for text in chunk_text(page.text, size, overlap):
            yield Chunk(page_no=page.number, index=idx, text=text)
            idx += 1
```

Notes:
- `iter_pages` is a generator function, so **nothing in its body runs until the first `next()`**, including `PdfReader(path)`. A bad file raises `ExtractError` when you start iterating, not when you call `iter_pages(...)`. The checkpoint calls `list(iter_pages(bad))` for exactly that reason.
- `enumerate(..., start=1)`: page numbers are for humans.
- Chunks never span pages: `chunk_text` runs per page. That keeps `page_no` exact, which matters more for citing than slightly better chunk boundaries.
- `_PARA` treats a blank line containing only spaces as a paragraph break too.

### 4. Your turn: `chunk_text`

```python
def chunk_text(text: str, size: int = 800, overlap: int = 100) -> Iterator[str]:
```

A generator implementing the algorithm above. The checkpoint checks these properties:
- `ValueError` if `size <= overlap`. (Why is that the condition? Think about the window step.)
- Empty or whitespace-only text yields nothing.
- **No chunk is ever longer than `size`**, for any text and any valid `size`/`overlap`, including `overlap=0` and `overlap=size-1`.
- **No text is lost**, including whatever was buffered before a giant paragraph.
- When the overlap fits, each chunk starts with the previous chunk's last `overlap` characters.
- Giant-paragraph windows cover the paragraph exactly, with no redundant final window: 550 chars at `size=300, overlap=50` gives exactly `[0:300]` and `[250:550]`.

<details><summary>Hint: structure</summary>

Validate, set `buf = ""`, loop over the stripped non-empty paragraphs. Handle the giant case first (flush the buffer, emit windows, reset, `continue`). Then try `candidate = f"{buf}\n\n{para}" if buf else para`. If it fits, keep it. If not, `yield buf` and compute the new buffer, with the tail only if `tail + "\n\n" + para` still fits. After the loop, flush.
</details>

<details><summary>Hint: overlap=0</summary>

`buf[-0:]` is the **whole** string, not the empty string, because `-0 == 0`. Guard it: `tail = buf[-overlap:] if overlap else ""`.
</details>

### 5. Try it on the samples

```bash
uv run python
>>> from pathlib import Path
>>> from docpipe.extract import iter_pages, iter_chunks
>>> pages = iter_pages(Path("../samples/sample_phonics.pdf"))
>>> pages                       # a generator: nothing has happened yet
>>> next(pages).text[:200]
>>> chunks = list(iter_chunks(Path("../samples/sample_training.pdf"), size=300, overlap=50))
>>> [(c.page_no, c.index, len(c.text)) for c in chunks]
```

## Checkpoint

```bash
uv run pytest ../checkpoints/test_dp_01_extract.py
uv run mypy src && uv run ruff check .
```

## Pitfalls

- **`buf[-overlap:]` with `overlap=0`** gives the whole buffer, so every chunk duplicates the previous one.
- **Forgetting the buffered text before a giant paragraph.** It's silent data loss: nothing crashes, a paragraph just never becomes searchable. The checkpoint's "no text is lost" test exists because an earlier version of this course's own reference had exactly this bug.
- **Expecting `iter_pages(bad)` to raise.** The call returns a generator. Errors appear on the first `next()`.
- **`except Exception: pass`** around extraction. You can't tell an empty PDF from a broken one.

## Explain it back

1. Why does `iter_pages(Path("bad.pdf"))` not raise, while `list(iter_pages(Path("bad.pdf")))` does?
2. Why must `size > overlap`? What happens to the window loop if they're equal?
3. Prove that `range(0, n - overlap, size - overlap)` windows reach the end of an `n`-character paragraph when `n > size`.
4. What does `raise X from e` add, and when would you use `from None`?
5. Why does library code use `logging.getLogger(__name__)` and never `basicConfig`?
6. Why are `Chunk` and `Page` dataclasses but `SearchHit` a Pydantic model?
