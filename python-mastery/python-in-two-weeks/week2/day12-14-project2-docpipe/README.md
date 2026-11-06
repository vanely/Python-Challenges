# Day 12–14: Project 2 — `docpipe`, PDF → chunks → SQLite full-text search → API (guided)

An end-to-end pipeline you'd actually deploy:

```
docpipe ingest ../samples --db docs.db         # extract, chunk, index (idempotent: skips unchanged files)
docpipe search "phonics" --db docs.db --limit 5
docpipe stats --db docs.db                     # polars report: pages, chunks, words per document
docpipe export out.jsonl --db docs.db          # one JSON object per chunk, streamed
docpipe serve --db docs.db                     # FastAPI on :8000 with /search, /documents, /export
```

Everything from both weeks shows up:
- generators for streaming pages and rows;
- dataclasses inside, Pydantic at the API boundary;
- context managers around the database;
- decorators;
- logging;
- polars, SQLite and FastAPI;
- tests with fixtures, and the full toolchain.

Five guided steps, each with concepts, code to type, a part you write yourself, and a checkpoint you didn't write:

| Step | File | You build | Checkpoint | Time |
|---|---|---|---|---|
| 1 | [steps/01-extract-and-chunk.md](steps/01-extract-and-chunk.md) | Scaffold, models, streaming PDF extraction, paragraph-aware chunking | `test_dp_01_extract.py` | ~2.5 h |
| 2 | [steps/02-store.md](steps/02-store.md) | SQLite schema, FTS5 index kept in sync by triggers, atomic replace, safe search | `test_dp_02_store.py` | ~3 h |
| 3 | [steps/03-pipeline.md](steps/03-pipeline.md) | Content-hash idempotency, per-file error boundary, timing decorator | `test_dp_03_pipeline.py` | ~1.5 h |
| 4 | [steps/04-cli-and-report.md](steps/04-cli-and-report.md) | typer CLI, logging setup, polars stats, streaming JSONL export | `test_dp_04_cli_report.py` | ~2 h |
| 5 | [steps/05-api.md](steps/05-api.md) | FastAPI app factory with lifespan, dependencies, validation, streaming | `test_dp_05_api.py` | ~2 h |

That's ~11 hours, not the 9 that three 3-hour days would give you. It's the biggest thing you've built in Python so far; give it four days if you need them. Answer every "Explain it back" question in `NOTES.md` next to this README.

## Setup

```bash
cd week2/day12-14-project2-docpipe
uv init --package docpipe
cd docpipe
```

Step 1 gives you the `pyproject.toml`. Run everything from `docpipe/`:

```bash
uv run pytest ../checkpoints/test_dp_01_extract.py
uv run pytest ../checkpoints                    # all of them; only once every step is done
```

Before the last step, run one checkpoint file at a time. Later checkpoint files import modules you haven't written yet, and pytest aborts the *whole* run when collection fails. Also, because the test paths point outside `docpipe/`, pytest ignores your `pyproject.toml`'s `[tool.pytest.ini_options]` for checkpoint runs. That only affects your own `uv run pytest`.

`../samples/` has two small PDFs for trying the CLI. Drop your own PDFs in there too.

## Readings

| Source | Where | Read |
|---|---|---|
| pypdf | https://pypdf.readthedocs.io/en/stable/user/extract-text.html | `PdfReader`, `page.extract_text()` |
| sqlite3 | https://docs.python.org/3/library/sqlite3.html | "How to use placeholders", "How to use the connection context manager", `Row` |
| SQLite FTS5 | https://www.sqlite.org/fts5.html | §1 overview, §3 query syntax, §4.4 external content tables, §5 `bm25()`/`snippet()` |
| `hashlib.file_digest` | https://docs.python.org/3/library/hashlib.html#file-hashing | 3.11+ |
| polars | https://docs.pola.rs/user-guide/concepts/expressions-and-contexts/ | Expressions, `with_columns`, `select` |
| FastAPI | https://fastapi.tiangolo.com/advanced/events/ | Lifespan events; "Dependencies"; "Handling Errors"; "Custom Response → StreamingResponse" |

## Reference implementation

`reference/docpipe/` is a complete, tested solution. **Open it only after all five checkpoints pass for your code.** Then diff it file by file and record the differences in `NOTES.md`.

```bash
cd reference/docpipe && uv sync
uv run pytest && uv run ruff check . && uv run mypy src tests
uv run docpipe ingest ../../samples --db docs.db
uv run docpipe search "phonics" --db docs.db
```
