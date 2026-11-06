"""Shared fixtures for the docpipe checkpoints. Run from your docpipe/ folder:

    uv run pytest ../checkpoints/test_dp_01_extract.py

`make_pdf` builds real PDFs with extractable text, so no binary fixtures are needed.
Your own tests can import it: `from conftest import make_pdf` only works here, so copy it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

PAGE_TEXTS = [
    "Phonics instruction teaches the relationship between letters and sounds.\n\n"
    "Systematic phonics moves from simple to complex patterns.",
    "Fluency is reading with accuracy, speed, and expression.\n\n"
    "Repeated reading builds fluency in early readers.",
]


def make_pdf(path: Path, pages: list[str] | None = None) -> Path:
    """Write a PDF with one page per string. An empty string makes a page with no text."""
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    for text in PAGE_TEXTS if pages is None else pages:
        page = writer.add_blank_page(width=612, height=792)
        ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
        for line in text.splitlines():
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            ops.append(f"({safe}) Tj T*")
        ops.append("ET")
        stream = StreamObject()
        stream._data = "\n".join(ops).encode("latin-1")
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
    with path.open("wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "sample.pdf")


@pytest.fixture
def store() -> Iterator[object]:
    from docpipe.store import Store

    with Store(":memory:") as s:
        yield s
