# Step 4 — CLI, logging setup, polars report, JSONL export

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/test_dp_04_cli_report.py`

## What you'll have at the end

A working `docpipe` command with `ingest`, `search`, `stats`, `export` and `serve`. `serve` stays a stub until step 5. A `report.py` turns store rows into a polars DataFrame.

## Concepts

### The application configures logging; libraries don't

Steps 1–3 only ever called `logging.getLogger(__name__)`. Nothing was printed unless you called `basicConfig` yourself in the REPL. That's correct for library code. The **CLI** is the application, so it decides the format and level, exactly once, before any command runs. A typer `@app.callback()` runs before every subcommand, which makes it the place for `-v/--verbose`:

```bash
docpipe -v ingest ../samples      # global options go BEFORE the subcommand
```

### Exit codes are an API

Scripts and CI read your exit code, not your colours:
- `0` means success.
- `1` means a runtime failure.
- `2` means bad usage. Click's convention, inherited by typer, is that `typer.BadParameter` and unknown options exit with 2 and print a usage hint.

A missing directory is a usage error, so raise `typer.BadParameter`.

### stdout is data, stderr is chatter

`docpipe search phonics --json | jq '.[0].path'` must receive **only** JSON on stdout. That's why `--json` uses plain `print(json.dumps(...))`, not rich (which may wrap long lines or add colour codes), and logging goes to stderr (`basicConfig`'s default).

### Rich markup and untrusted text

`rich` treats `[green]...[/green]` as markup, so text containing square brackets is at risk. Specifically, anything that looks like a tag is at risk: a bracket followed by a lowercase letter, `/`, `#` or `@`. Our snippets contain highlights from step 2. `[Phonics]` would survive, but `[phonics]` would be silently swallowed as an unknown style tag, and only for some queries, which makes it a nasty bug to chase. Data from outside (file contents, user input) goes through `rich.markup.escape()` before it's printed through rich.

### polars in one paragraph

A `DataFrame` is a set of typed columns. You transform it with **expressions** (`pl.col("words") / pl.col("pages")`), which polars plans and runs in Rust, in parallel, without Python loops:
- `with_columns(name=expr)` adds or replaces columns.
- `select(...)` picks and orders them.
- `df["col"].sum()` reduces a column.

The scalar you get back is a Python `int` or `float` for most dtypes, but the type checker sees a broad union, so wrap it in `int(...)` when you promise `dict[str, int]`.

### JSON Lines

`.jsonl` is one JSON object per line. Unlike a JSON array, you can write it **while streaming** (no closing `]` to wait for) and read it line by line, and it's what most data tools (`jq`, polars `read_ndjson`, BigQuery) ingest natively.

## Build

### 1. `src/docpipe/cli.py`, minus `stats` and `export`

```python
"""docpipe CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from docpipe.pipeline import ingest_dir
from docpipe.report import stats_frame, totals
from docpipe.store import Store

app = typer.Typer(help="PDF ingestion and search.", no_args_is_help=True)
console = Console()

DbOpt = Annotated[Path, typer.Option("--db", help="SQLite database path.")]


@app.callback()
def _setup(verbose: Annotated[bool, typer.Option("-v", "--verbose")] = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)-7s %(name)s: %(message)s",
    )


@app.command()
def ingest(
    directory: Path,
    db: DbOpt = Path("docs.db"),
    force: Annotated[bool, typer.Option(help="Re-ingest even if unchanged.")] = False,
) -> None:
    """Ingest every *.pdf under DIRECTORY."""
    if not directory.is_dir():
        raise typer.BadParameter(f"{directory} is not a directory")
    with Store(db) as store:
        r = ingest_dir(directory, store, force=force)
    console.print(
        f"[green]ingested[/green] {r.ingested}  skipped {r.skipped}  "
        f"[red]failed[/red] {r.failed}  chunks {r.chunks}  ({r.seconds:.2f}s)"
    )


@app.command()
def search(
    query: str,
    db: DbOpt = Path("docs.db"),
    limit: Annotated[int, typer.Option(min=1, max=50)] = 10,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Full-text search over ingested chunks."""
    with Store(db) as store:
        hits = store.search(query, limit)
    if as_json:
        print(json.dumps([h.model_dump() for h in hits], indent=2))
        return
    t = Table(title=f"{len(hits)} hit(s) for {query!r}")
    t.add_column("Doc", overflow="fold")
    t.add_column("Page", justify="right")
    t.add_column("Score", justify="right")
    t.add_column("Snippet", overflow="fold")
    for h in hits:
        t.add_row(
            Path(h.path).name,
            str(h.page_no),
            f"{h.score:.2f}",
            escape(h.snippet.replace("\n", " ")),
        )
    console.print(t)


@app.command()
def serve(db: DbOpt = Path("docs.db"), port: int = 8000) -> None:
    """Run the search API."""
    import uvicorn

    from docpipe.api import create_app

    uvicorn.run(create_app(db), host="127.0.0.1", port=port)


if __name__ == "__main__":
    app()
```

- The `[project.scripts]` entry from step 1 (`docpipe = "docpipe.cli:app"`) makes `uv run docpipe` work.
- `DbOpt` is a reusable annotated type: one definition, the same `--db` option on every command.
- `typer.Option(min=1, max=50)` validates the range before your code runs, and a bad value exits with 2.
- `serve` imports uvicorn and the API **inside** the function, so `docpipe search` doesn't pay for importing FastAPI. mypy still checks that import, so create a placeholder `src/docpipe/api.py` now; step 5 replaces it:

  ```python
  """FastAPI app — written in step 5."""

  from pathlib import Path

  from fastapi import FastAPI


  def create_app(db_path: Path | str) -> FastAPI:
      raise NotImplementedError("step 5")
  ```
- `as_json` with `"--json"`: the parameter can't be called `json` without shadowing the module.
- The **`with Store(db) as store:` block ends before printing**. Close the database as soon as you're done with it.

### 2. Your turn: `src/docpipe/report.py`

```python
def stats_frame(store: Store) -> pl.DataFrame: ...
def totals(df: pl.DataFrame) -> dict[str, int]: ...
```

`stats_frame`, built from `store.stats_rows()`:
- Columns, exactly in this order: `path, pages, chunks, words, words_per_page`.
- `path` is the **file name only**. Keys are POSIX paths (step 3), so split on `/`.
- `words_per_page` is words ÷ pages rounded to 1 decimal. A 0-page document must not divide by zero: it gives `0.0`.
- An empty store returns an **empty frame with the same five columns** and proper dtypes. `pl.DataFrame([])` has no columns at all, so code downstream that selects `"words"` would crash.

`totals`: `{"documents", "pages", "chunks", "words"}` as plain Python `int`s, all zeros for an empty frame.

<details><summary>Hint: polars expressions you'll need</summary>

`pl.col("path").str.split("/").list.last()`, `pl.col("pages").clip(1)` (it's a floor: values below 1 become 1, and 0 words ÷ 1 is 0), `.round(1)`, and `pl.DataFrame(schema={"path": pl.Utf8, ...})` for the empty case.
</details>

### 3. Your turn: `stats` and `export` commands

- `docpipe stats [--db]` prints the stats frame, then the totals.
- `docpipe export OUT [--db]` writes `store.iter_chunks()` as JSON Lines to `OUT` (UTF-8), **streaming**: one row in memory at a time. Finish with `wrote N chunks to OUT`.

<details><summary>Hint: two context managers, one `with`</summary>

`with Store(db) as store, out.open("w", encoding="utf-8") as f:`. Both close on exit, in reverse order. Always pass `encoding=`: on Windows the default is the locale code page, not UTF-8, until Python 3.15 (PEP 686).
</details>

### 4. Run it for real

```bash
uv run docpipe ingest ../samples --db try.db
uv run docpipe ingest ../samples --db try.db          # skipped 2
uv run docpipe -v ingest ../samples --db try.db --force
uv run docpipe search "phonics" --db try.db
uv run docpipe search "phonics" --db try.db --json
uv run docpipe stats --db try.db
uv run docpipe export out.jsonl --db try.db
uv run docpipe ingest nope --db try.db; echo "exit=$?"     # 2
```

## Checkpoint

```bash
uv run pytest ../checkpoints/test_dp_04_cli_report.py
uv run mypy src && uv run ruff check .
```

## Pitfalls

- **`docpipe ingest ../samples -v`.** `-v` belongs to the callback, so it goes before the subcommand. After it, typer reports "No such option".
- **Printing JSON through rich.** It soft-wraps long lines, and the output stops being valid JSON when piped.
- **Unescaped snippets.** `[phonics]` disappears and you think search highlighting is broken.
- **`open(out, "w")` with no encoding.** It works on your Mac and breaks on a colleague's Windows box with the first `é`.
- **`json.dumps(list(store.iter_chunks()))`.** It works, and it holds the whole corpus in memory twice.
- **Returning a polars scalar or a numpy integer from `totals`.** `json.dumps` and some equality checks behave differently from a plain `int`. Convert at the boundary.

## Explain it back

1. Why does `basicConfig` belong in the CLI callback and nowhere in `extract.py` or `pipeline.py`?
2. What exit code does a missing directory produce, and why that one?
3. Why is `--json` output printed with `print` and not `console.print`?
4. What would the search table show for a snippet `"teach [phonics] early"` without `escape`?
5. Why does an empty `stats_frame` need an explicit schema?
6. Why is JSONL a better export format than one big JSON array?
