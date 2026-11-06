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
def stats(db: DbOpt = Path("docs.db")) -> None:
    """Per-document statistics."""
    with Store(db) as store:
        df = stats_frame(store)
    console.print(df)
    console.print(totals(df))


@app.command()
def export(out: Path, db: DbOpt = Path("docs.db")) -> None:
    """Write every chunk as JSON Lines."""
    n = 0
    with Store(db) as store, out.open("w", encoding="utf-8") as f:
        for row in store.iter_chunks():
            f.write(json.dumps(row) + "\n")
            n += 1
    console.print(f"wrote {n} chunks to {out}")


@app.command()
def serve(db: DbOpt = Path("docs.db"), port: int = 8000) -> None:
    """Run the search API."""
    import uvicorn

    from docpipe.api import create_app

    uvicorn.run(create_app(db), host="127.0.0.1", port=port)


if __name__ == "__main__":
    app()
