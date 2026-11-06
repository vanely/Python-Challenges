"""Fixtures: a generated multi-page PDF, a fresh in-memory Store, and a populated one."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from pypdf import PdfWriter

from docpipe.store import Store

PAGE_TEXTS = [
    "Phonics instruction teaches the relationship between letters and sounds.\n\n"
    "Systematic phonics moves from simple to complex patterns.",
    "Fluency is reading with accuracy, speed, and expression.\n\n"
    "Repeated reading builds fluency in early readers.",
]


def make_pdf(path: Path, pages: list[str] = PAGE_TEXTS) -> Path:
    """Build a real PDF with extractable text using pypdf's writer + a minimal content stream."""
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
        StreamObject,
    )

    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        lines = text.replace("\n\n", "\n").splitlines()
        ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            ops.append(f"({safe}) Tj T*")
        ops.append("ET")
        stream = StreamObject()
        stream._data = "\n".join(ops).encode("latin-1")
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        _ = (ArrayObject, FloatObject, NumberObject)  # keep imports used if you extend this
    with path.open("wb") as f:
        writer.write(f)
    return path


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "sample.pdf")


@pytest.fixture
def store() -> Iterator[Store]:
    with Store(":memory:") as s:
        yield s


@pytest.fixture
def populated(store: Store, pdf: Path) -> Store:
    from docpipe.pipeline import ingest_file

    ingest_file(pdf, store)
    return store
