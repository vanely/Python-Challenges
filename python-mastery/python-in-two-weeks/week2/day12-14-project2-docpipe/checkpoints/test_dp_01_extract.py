"""Step 1: models and extraction. Spec: steps/01-extract-and-chunk.md."""

from __future__ import annotations

import dataclasses
import inspect
import logging
import re
from pathlib import Path

import pytest
from conftest import make_pdf

from docpipe.extract import ExtractError, chunk_text, iter_chunks, iter_pages
from docpipe.models import Chunk, Page


def test_models_are_frozen_dataclasses() -> None:
    c = Chunk(page_no=1, index=0, text="one two  three\nfour")
    assert c.word_count == 4
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.text = "x"  # type: ignore[misc]
    assert Page(number=1, text="t").number == 1


def test_iter_pages_numbers_from_one(pdf: Path) -> None:
    pages = list(iter_pages(pdf))
    assert [p.number for p in pages] == [1, 2]
    assert "Phonics" in pages[0].text and "Fluency" in pages[1].text


def test_iter_pages_is_lazy() -> None:
    assert inspect.isgeneratorfunction(iter_pages)


def test_text_is_cleaned(tmp_path: Path) -> None:
    p = make_pdf(tmp_path / "ws.pdf", ["  lots    of\t\tspaces   \n   indented line   "])
    (page,) = iter_pages(p)
    assert "  " not in page.text and "\t" not in page.text
    assert page.text == page.text.strip()
    assert all(line == line.strip() for line in page.text.splitlines())


def test_empty_page_is_yielded_and_logged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    p = make_pdf(tmp_path / "scan.pdf", ["first page", "", "third page"])
    with caplog.at_level(logging.INFO):
        pages = list(iter_pages(p))
    assert [pg.number for pg in pages] == [1, 2, 3]
    assert pages[1].text == ""
    assert any("2" in r.getMessage() and "scan.pdf" in r.getMessage() for r in caplog.records), (
        "log the file name and page number of empty pages"
    )


def test_bad_pdf_raises_extract_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with pytest.raises(ExtractError) as ei:
        list(iter_pages(bad))
    assert ei.value.path == bad
    assert "bad.pdf" in str(ei.value)
    assert ei.value.__cause__ is not None, "chain the original error: raise ... from e"


def test_chunk_text_validates() -> None:
    with pytest.raises(ValueError):
        list(chunk_text("x", size=10, overlap=10))


def test_chunk_text_empty() -> None:
    assert list(chunk_text("")) == []
    assert list(chunk_text("\n\n  \n\n")) == []


def test_small_text_is_one_chunk() -> None:
    assert list(chunk_text("para one\n\npara two", size=100, overlap=10)) == [
        "para one\n\npara two"
    ]


def _paragraphs(n: int, width: int) -> str:
    return "\n\n".join(f"p{i:02d} " + "x" * (width - 4) for i in range(n))


@pytest.mark.parametrize(("size", "overlap"), [(100, 20), (300, 100), (120, 0), (80, 79)])
def test_chunks_never_exceed_size(size: int, overlap: int) -> None:
    text = _paragraphs(12, 37) + "\n\n" + "y" * 700 + "\n\n" + _paragraphs(5, 70)
    chunks = list(chunk_text(text, size=size, overlap=overlap))
    assert chunks and all(len(c) <= size for c in chunks), [len(c) for c in chunks]


def test_no_paragraph_is_lost() -> None:
    text = "intro para\n\n" + "y" * 400 + "\n\n" + _paragraphs(8, 30)
    joined = "\n".join(chunk_text(text, size=150, overlap=30))
    assert "intro para" in joined, "text buffered before a giant paragraph must be yielded"
    for i in range(8):
        assert f"p{i:02d}" in joined


def test_overlap_carries_the_tail_forward() -> None:
    chunks = list(chunk_text(_paragraphs(10, 30), size=100, overlap=20))
    assert len(chunks) > 3
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert b.startswith(a[-20:]), (a, b)


def test_giant_paragraph_windows_cover_everything_without_redundancy() -> None:
    para = "".join(chr(ord("a") + i % 26) for i in range(550))
    chunks = list(chunk_text(para, size=300, overlap=50))
    assert chunks == [para[0:300], para[250:550]], "last window ends exactly at the end"
    big = "z" * 1000
    pieces = list(chunk_text(big, size=300, overlap=50))
    assert [len(p) for p in pieces] == [300, 300, 300, 250]


def test_iter_chunks_indexes_across_pages(pdf: Path) -> None:
    chunks = list(iter_chunks(pdf, size=60, overlap=10))
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert {c.page_no for c in chunks} == {1, 2}
    assert all(isinstance(c, Chunk) for c in chunks)
    first_on_page_2 = next(c for c in chunks if c.page_no == 2)
    assert re.match(r"Fluency", first_on_page_2.text), "chunks never span pages"
