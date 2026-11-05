from pathlib import Path

import pytest

from docpipe.extract import ExtractError, chunk_text, iter_chunks, iter_pages


def test_iter_pages(pdf: Path) -> None:
    pages = list(iter_pages(pdf))
    assert [p.number for p in pages] == [1, 2]
    assert "Phonics" in pages[0].text
    assert "Fluency" in pages[1].text


def test_iter_chunks_indexes_across_pages(pdf: Path) -> None:
    chunks = list(iter_chunks(pdf, size=60, overlap=10))
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert {c.page_no for c in chunks} == {1, 2}


def test_chunk_text_respects_size_and_overlap() -> None:
    text = "\n\n".join(f"para {i} " + "x" * 30 for i in range(10))
    chunks = list(chunk_text(text, size=100, overlap=20))
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) > 3
    # overlap: the tail of chunk n appears at the head of chunk n+1
    assert chunks[0][-20:] == chunks[1][:20]


def test_chunk_text_splits_giant_paragraph() -> None:
    chunks = list(chunk_text("y" * 1000, size=300, overlap=50))
    assert all(len(c) <= 300 for c in chunks)
    assert "".join(c[:250] for c in chunks).startswith("y" * 250)


def test_chunk_text_validates() -> None:
    with pytest.raises(ValueError, match="exceed"):
        list(chunk_text("x", size=10, overlap=10))


def test_bad_pdf_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(ExtractError):
        list(iter_pages(bad))
