"""Ingestion: walk a directory, skip unchanged files, extract -> chunk -> store."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from pypdf import PdfReader

from docpipe.extract import ExtractError, iter_chunks
from docpipe.models import IngestReport
from docpipe.store import Store
from docpipe.util import sha256_of, timed

log = logging.getLogger(__name__)


@timed
def ingest_file(path: Path, store: Store, *, force: bool = False) -> int:
    """Returns number of chunks stored, or -1 if skipped as unchanged."""
    key = path.resolve().as_posix()  # forward slashes on every OS
    digest = sha256_of(path)
    existing = store.find_by_path(key)
    if existing and existing.sha256 == digest and not force:
        return -1
    chunks = list(iter_chunks(path))  # materialise: we need the count + one txn
    pages = len(PdfReader(path).pages)  # cheap: no text extraction; iter_chunks proved it opens
    store.replace_document(key, digest, pages, chunks)
    return len(chunks)


def ingest_dir(directory: Path, store: Store, *, force: bool = False) -> IngestReport:
    t0 = time.perf_counter()
    report = IngestReport()
    for path in sorted(directory.rglob("*.pdf")):
        try:
            n = ingest_file(path, store, force=force)
        except ExtractError as e:  # expected: not a PDF, encrypted, truncated
            log.error("skipping %s", e)  # ExtractError's message already starts with the path
            report.failed += 1
            continue
        except Exception:  # per-file boundary: one bad file never stops the batch
            log.exception("failed: %s", path)
            report.failed += 1
            continue
        if n < 0:
            log.info("unchanged: %s", path.name)
            report.skipped += 1
        else:
            log.info("ingested: %s (%d chunks)", path.name, n)
            report.ingested += 1
            report.chunks += n
    report.seconds = time.perf_counter() - t0
    return report
