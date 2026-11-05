"""Ingestion: walk a directory, skip unchanged files, extract -> chunk -> store."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from docpipe.extract import ExtractError, iter_chunks, iter_pages
from docpipe.models import IngestReport
from docpipe.store import Store
from docpipe.util import sha256_of, timed

log = logging.getLogger(__name__)


@timed
def ingest_file(path: Path, store: Store, *, force: bool = False) -> int:
    """Returns number of chunks stored, or -1 if skipped as unchanged."""
    key = str(path.resolve())
    digest = sha256_of(path)
    existing = store.find_by_path(key)
    if existing and existing.sha256 == digest and not force:
        return -1
    pages = sum(1 for _ in iter_pages(path))  # cheap second pass for the page count
    chunks = list(iter_chunks(path))  # materialise: we need the count + one txn
    store.replace_document(key, digest, pages, chunks)
    return len(chunks)


def ingest_dir(directory: Path, store: Store, *, force: bool = False) -> IngestReport:
    t0 = time.perf_counter()
    report = IngestReport()
    for path in sorted(directory.rglob("*.pdf")):
        try:
            n = ingest_file(path, store, force=force)
        except ExtractError as e:
            log.error("skipping %s: %s", path.name, e)
            report.failed += 1
            continue
        except OSError:
            log.exception("unreadable: %s", path)
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
