import pytest

from docpipe.models import Chunk
from docpipe.store import DocumentNotFound, Store


def test_replace_and_search(store: Store) -> None:
    chunks = [Chunk(1, 0, "systematic phonics instruction"), Chunk(2, 1, "reading fluency")]
    doc_id = store.replace_document("/a.pdf", "abc", 2, chunks)
    assert store.chunk_count(doc_id) == 2
    hits = store.search("phonics")
    assert len(hits) == 1 and hits[0].page_no == 1 and "[phonics]" in hits[0].snippet


def test_replace_is_idempotent(store: Store) -> None:
    store.replace_document("/a.pdf", "v1", 1, [Chunk(1, 0, "alpha")])
    store.replace_document("/a.pdf", "v2", 1, [Chunk(1, 0, "beta")])
    assert len(store.list_documents()) == 1
    assert store.search("alpha") == []
    assert len(store.search("beta")) == 1


def test_stemming_and_quoting(store: Store) -> None:
    store.replace_document("/a.pdf", "x", 1, [Chunk(1, 0, "teaching readers to read")])
    assert store.search("teach") != []  # porter stemmer
    assert store.search('read" OR "x') == []  # injection-safe: quoted literally


def test_get_missing(store: Store) -> None:
    with pytest.raises(DocumentNotFound):
        store.get(42)


def test_stats_and_iter(store: Store) -> None:
    store.replace_document("/a.pdf", "x", 3, [Chunk(1, 0, "one two"), Chunk(2, 1, "three")])
    rows = store.stats_rows()
    assert rows[0]["chunks"] == 2 and rows[0]["words"] == 3
    assert [r["chunk_index"] for r in store.iter_chunks()] == [0, 1]
