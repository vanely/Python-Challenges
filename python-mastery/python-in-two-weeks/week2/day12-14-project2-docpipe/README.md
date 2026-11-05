# Day 12–14: Project 2 — `docpipe`, PDF → structured JSON → SQLite → search API

An end-to-end pipeline you'd actually deploy: ingest a folder of PDFs, extract and chunk their text,
store chunks with metadata in SQLite with full-text search, and serve a typed FastAPI search endpoint.
Everything from both weeks shows up: generators for streaming pages, dataclasses/Pydantic at the right
layers, context managers around the DB, decorators for timing/retry, async for the API, polars for a stats
report, logging, pathlib, subprocess (optional OCR), tests with fixtures, and the full toolchain.

## What you'll build
```
docpipe ingest ./samples --db docs.db          # extract, chunk, index (idempotent; skips unchanged files)
docpipe search "phonics" --db docs.db --limit 5
docpipe stats --db docs.db                     # polars report: docs, pages, chunks, words per doc
docpipe serve --db docs.db                     # FastAPI on :8000 with /search?q=...&limit=5 and /docs/{id}
docpipe export --db docs.db out.jsonl          # one JSON object per chunk
```

## Readings for the project

| Source | Where | Read |
|---|---|---|
| pypdf | https://pypdf.readthedocs.io/en/stable/user/extract-text.html | Extract text; `PdfReader`, `page.extract_text()` |
| SQLite FTS5 | https://www.sqlite.org/fts5.html | Overview, `MATCH`, `bm25()`, `snippet()`, external-content tables |
| `hashlib` | https://docs.python.org/3/library/hashlib.html | `file_digest` (3.11) |
| FastAPI background/streaming | https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse | For `export` over HTTP (stretch) |
| polars | https://docs.pola.rs/user-guide/concepts/expressions/ | Refresher |
| Everything from Days 8–11 | — | You'll reuse it all |

Key points:
- `pypdf` is pure Python; text extraction quality varies by PDF. Treat `extract_text()` returning `""` as "scanned page" and log it. OCR (`pytesseract`) is an optional stretch behind a flag.
- Chunking: split on paragraphs, then merge to ~800 characters with ~100 overlap. Keep `page_no` and `chunk_index` so you can cite back.
- Idempotency: hash the file bytes (`hashlib.file_digest`); store the hash on the document row; skip if unchanged, re-ingest if changed.
- FTS5 external-content table over `chunks` keeps one copy of the text. Use `bm25()` for ranking and `snippet()` for highlights.

## Build plan

### Day 12 — extraction and storage (~3 hrs)
1. Skeleton from Day 5 template. `uv add pypdf fastapi uvicorn typer rich polars pydantic`.
2. `models.py`: `Document`, `Page`, `Chunk` dataclasses. `SearchHit` Pydantic model (API boundary).
3. `extract.py`: `iter_pages(path) -> Iterator[Page]` (generator; logs empty pages). `chunk_text(text, size, overlap) -> Iterator[str]`.
4. `store.py`: `Store` class — context manager over `sqlite3`, `SCHEMA` with `documents`, `chunks`, `chunks_fts` (FTS5, external content, triggers to keep in sync). Methods: `upsert_document`, `add_chunks`, `search`, `stats_rows`, `iter_chunks`.
5. Test `extract.py` with a tiny generated PDF (see `tests/conftest.py` — it builds one with pypdf's writer) and `store.py` with `:memory:`.

### Day 13 — pipeline, CLI, report (~3 hrs)
6. `pipeline.py`: `ingest_dir(dir, store) -> IngestReport` — walks `rglob("*.pdf")`, hashes, skips unchanged, extracts → chunks → stores in one transaction per file; `@timed` decorator; per-file errors logged and counted, never fatal.
7. `cli.py`: typer commands `ingest`, `search`, `stats`, `export`, `serve`. Rich table for search results with snippets.
8. `report.py`: polars from `stats_rows()`; print docs/pages/chunks/words per document, and top terms (stretch).
9. `export`: JSON Lines via `iter_chunks()` generator — never load everything into memory.

### Day 14 — API, tests, polish (~3 hrs)
10. `api.py`: FastAPI with lifespan opening the `Store`; `GET /search` (q, limit ≤ 50) → `list[SearchHit]`; `GET /documents` and `GET /documents/{id}`; 404 handler; `TestClient` tests with a temp DB.
11. Full test suite green; `ruff`, `mypy --strict` clean.
12. Write `NOTES.md`: what surprised you, where you wrote TS-in-Python, what you'd do differently. This is the reflection that turns the project into learning.
13. Stretch: async ingestion with `asyncio.to_thread` per file + `Semaphore(4)`; `--ocr` flag using `subprocess` + `tesseract`; a `/export` `StreamingResponse`.

## Reference implementation
`docpipe/` is a complete, tested solution (~450 lines). Build yours first. Then diff.

```bash
cd docpipe && uv sync
uv run pytest && uv run ruff check . && uv run mypy src
uv run docpipe ingest samples --db /tmp/docs.db
uv run docpipe search "sample" --db /tmp/docs.db
uv run docpipe stats --db /tmp/docs.db
uv run docpipe serve --db /tmp/docs.db    # then open http://127.0.0.1:8000/docs
```
`samples/` contains two small generated PDFs. Drop any of your own PDFs in there.
