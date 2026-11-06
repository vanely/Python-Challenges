"""PDF text extraction and chunking. Both are generators: nothing is held in memory."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path

from pypdf import PdfReader

from docpipe.models import Chunk, Page

log = logging.getLogger(__name__)
_PARA = re.compile(r"\n\s*\n")
_WS = re.compile(r"[ \t]+")


class ExtractError(Exception):
    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path


def iter_pages(path: Path) -> Iterator[Page]:
    try:
        reader = PdfReader(path)
    except Exception as e:  # pypdf raises a zoo of exception types
        raise ExtractError(path, f"cannot open PDF ({type(e).__name__}: {e})") from e
    for i, page in enumerate(reader.pages, start=1):
        text = _clean(page.extract_text() or "")
        if not text:
            log.info("%s page %d: no text (scanned?)", path.name, i)
        yield Page(number=i, text=text)


def _clean(text: str) -> str:
    text = _WS.sub(" ", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> Iterator[str]:
    """Paragraph-aware chunks of at most `size` chars.

    Paragraphs are packed greedily. A new chunk starts with the last `overlap` chars of the
    previous one when that still fits. Paragraphs longer than `size` are split into windows
    of `size` that advance by `size - overlap`.
    """
    if size <= overlap:
        raise ValueError("size must exceed overlap")
    buf = ""
    for para in (p.strip() for p in _PARA.split(text) if p.strip()):
        if len(para) > size:  # hard-split giant paragraphs
            if buf:
                yield buf
            for i in range(0, len(para) - overlap, size - overlap):
                yield para[i : i + size]
            buf = ""
            continue
        candidate = f"{buf}\n\n{para}" if buf else para
        if len(candidate) <= size:
            buf = candidate
            continue
        yield buf
        tail = buf[-overlap:] if overlap else ""
        with_tail = f"{tail}\n\n{para}"
        buf = with_tail if tail and len(with_tail) <= size else para
    if buf:
        yield buf


def iter_chunks(path: Path, size: int = 800, overlap: int = 100) -> Iterator[Chunk]:
    idx = 0
    for page in iter_pages(path):
        for text in chunk_text(page.text, size, overlap):
            yield Chunk(page_no=page.number, index=idx, text=text)
            idx += 1
