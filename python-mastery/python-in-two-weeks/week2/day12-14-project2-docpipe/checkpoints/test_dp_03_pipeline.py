"""Step 3: the ingestion pipeline. Spec: steps/03-pipeline.md."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import make_pdf

import docpipe.extract
from docpipe.models import IngestReport, Page
from docpipe.pipeline import ingest_dir, ingest_file
from docpipe.store import Store


def test_ingest_file_stores_chunks_and_pages(tmp_path: Path, store: Store) -> None:
    p = make_pdf(tmp_path / "a.pdf")
    n = ingest_file(p, store)
    assert n >= 2
    (doc,) = store.list_documents()
    assert doc.pages == 2
    assert store.chunk_count(doc.id) == n
    assert doc.path == p.resolve().as_posix(), "store absolute paths with forward slashes"
    assert len(doc.sha256) == 64


def test_unchanged_file_is_skipped_and_force_reingests(tmp_path: Path, store: Store) -> None:
    p = make_pdf(tmp_path / "a.pdf")
    ingest_file(p, store)
    assert ingest_file(p, store) == -1
    assert ingest_file(p, store, force=True) >= 1
    assert len(store.list_documents()) == 1


def test_changed_file_is_reingested(tmp_path: Path, store: Store) -> None:
    p = make_pdf(tmp_path / "a.pdf", ["original text"])
    ingest_file(p, store)
    make_pdf(p, ["completely different"])
    assert ingest_file(p, store) >= 1
    assert store.search("original") == []
    assert len(store.search("different")) == 1


def test_ingest_dir_counts(tmp_path: Path, store: Store) -> None:
    make_pdf(tmp_path / "a.pdf")
    (tmp_path / "sub").mkdir()
    make_pdf(tmp_path / "sub" / "b.pdf")
    (tmp_path / "bad.pdf").write_bytes(b"nope")
    (tmp_path / "notes.txt").write_text("ignored")

    r1 = ingest_dir(tmp_path, store)
    assert isinstance(r1, IngestReport)
    assert (r1.ingested, r1.skipped, r1.failed) == (2, 0, 1)
    assert r1.chunks == sum(r["chunks"] for r in store.stats_rows())
    assert r1.seconds > 0
    r2 = ingest_dir(tmp_path, store)
    assert (r2.ingested, r2.skipped, r2.failed, r2.chunks) == (0, 2, 1, 0)
    r3 = ingest_dir(tmp_path, store, force=True)
    assert r3.ingested == 2


def test_unexpected_error_mid_file_is_counted_not_fatal(
    tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    make_pdf(tmp_path / "a.pdf")
    make_pdf(tmp_path / "boom.pdf")
    make_pdf(tmp_path / "c.pdf")
    real = docpipe.extract.iter_pages

    def flaky(path: Path) -> Iterator[Page]:
        for page in real(path):
            if path.name == "boom.pdf" and page.number == 2:
                raise RuntimeError("pypdf choked on page 2")
            yield page

    monkeypatch.setattr(docpipe.extract, "iter_pages", flaky)
    with caplog.at_level(logging.ERROR):
        r = ingest_dir(tmp_path, store)
    assert (r.ingested, r.failed) == (2, 1)
    assert any("boom.pdf" in rec.getMessage() for rec in caplog.records)
    assert any(rec.exc_info for rec in caplog.records), "log.exception keeps the traceback"
    assert {Path(d.path).name for d in store.list_documents()} == {"a.pdf", "c.pdf"}


def test_failed_reingest_keeps_previous_version(
    tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_pdf(tmp_path / "a.pdf", ["version one", "page two"])
    ingest_file(p, store)
    (before,) = store.list_documents()
    make_pdf(p, ["version two", "page two"])
    real = docpipe.extract.iter_pages

    def dies_on_page_2(path: Path) -> Iterator[Page]:
        for page in real(path):
            if page.number == 2:
                raise RuntimeError("boom")
            yield page

    monkeypatch.setattr(docpipe.extract, "iter_pages", dies_on_page_2)
    r = ingest_dir(tmp_path, store)
    assert r.failed == 1
    (after,) = store.list_documents()
    assert after.sha256 == before.sha256, "the failed re-ingest must not replace anything"
    assert len(store.search("one")) == 1, "old version still searchable"
