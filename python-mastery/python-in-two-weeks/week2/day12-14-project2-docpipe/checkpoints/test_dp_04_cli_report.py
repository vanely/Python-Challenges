"""Step 4: the CLI and the polars report. Spec: steps/04-cli-and-report.md."""

from __future__ import annotations

import json
import re
from pathlib import Path

import polars as pl
from conftest import make_pdf
from typer.testing import CliRunner

from docpipe.cli import app
from docpipe.pipeline import ingest_file
from docpipe.report import stats_frame, totals
from docpipe.store import Store

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def plain(text: str) -> str:
    return _ANSI.sub("", text)


def test_stats_frame(tmp_path: Path, store: Store) -> None:
    ingest_file(make_pdf(tmp_path / "a.pdf"), store)
    ingest_file(make_pdf(tmp_path / "b.pdf", ["just one page of words"]), store)
    df = stats_frame(store)
    assert df.columns == ["path", "pages", "chunks", "words", "words_per_page"]
    assert df["path"].to_list() == ["a.pdf", "b.pdf"], "file names only, sorted"
    assert df["pages"].to_list() == [2, 1]
    b = df.row(1, named=True)
    assert b["words"] == 5 and b["words_per_page"] == 5.0


def test_stats_frame_empty(store: Store) -> None:
    df = stats_frame(store)
    assert df.is_empty()
    assert df.columns == ["path", "pages", "chunks", "words", "words_per_page"], (
        "same schema whether or not there is data"
    )
    assert totals(df) == {"documents": 0, "pages": 0, "chunks": 0, "words": 0}


def test_totals(tmp_path: Path, store: Store) -> None:
    ingest_file(make_pdf(tmp_path / "a.pdf"), store)
    t = totals(stats_frame(store))
    assert t["documents"] == 1 and t["pages"] == 2 and t["words"] > 10
    assert all(type(v) is int for v in t.values()), "plain ints, not numpy/polars scalars"


def test_zero_page_document_does_not_divide_by_zero(store: Store) -> None:
    store.replace_document("/empty.pdf", "h", 0, [])
    df = stats_frame(store)
    assert df["words_per_page"].to_list() == [0.0]


def _ingest(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    make_pdf(docs / "a.pdf")
    db = tmp_path / "t.db"
    result = runner.invoke(app, ["ingest", str(docs), "--db", str(db)])
    assert result.exit_code == 0, result.output
    assert "ingested" in plain(result.output).lower()
    return db


def test_cli_ingest_twice_skips(tmp_path: Path) -> None:
    db = _ingest(tmp_path)
    again = runner.invoke(app, ["ingest", str(tmp_path / "docs"), "--db", str(db)])
    assert again.exit_code == 0
    assert re.search(r"skipped\D*1", plain(again.output)), again.output


def test_cli_ingest_rejects_missing_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["ingest", str(tmp_path / "nope"), "--db", str(tmp_path / "x.db")])
    assert result.exit_code == 2


def test_cli_search_json(tmp_path: Path) -> None:
    db = _ingest(tmp_path)
    result = runner.invoke(app, ["search", "phonics", "--db", str(db), "--json"])
    assert result.exit_code == 0, result.output
    hits = json.loads(result.stdout)
    assert hits and hits[0]["page_no"] == 1 and "[" in hits[0]["snippet"]


def test_cli_search_table_escapes_brackets(tmp_path: Path) -> None:
    db = _ingest(tmp_path)
    result = runner.invoke(app, ["search", "phonics", "--db", str(db)])
    assert result.exit_code == 0, result.output
    assert "[Phonics]" in plain(result.stdout) or "[phonics]" in plain(result.stdout), (
        "rich treats [x] as markup; escape snippets so the highlight brackets show"
    )


def test_cli_export_jsonl(tmp_path: Path) -> None:
    db = _ingest(tmp_path)
    out = tmp_path / "out.jsonl"
    result = runner.invoke(app, ["export", str(out), "--db", str(db)])
    assert result.exit_code == 0, result.output
    lines = out.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    assert rows and {"path", "page_no", "chunk_index", "text"} <= set(rows[0])
    assert [r["chunk_index"] for r in rows] == list(range(len(rows)))


def test_cli_stats(tmp_path: Path) -> None:
    db = _ingest(tmp_path)
    result = runner.invoke(app, ["stats", "--db", str(db)])
    assert result.exit_code == 0, result.output
    assert "a.pdf" in plain(result.stdout)


def test_stats_frame_returns_a_dataframe(store: Store) -> None:
    assert isinstance(stats_frame(store), pl.DataFrame)
