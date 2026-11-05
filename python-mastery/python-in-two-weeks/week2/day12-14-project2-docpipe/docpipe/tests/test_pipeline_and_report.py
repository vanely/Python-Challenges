from pathlib import Path

from docpipe.pipeline import ingest_dir, ingest_file
from docpipe.report import stats_frame, totals
from docpipe.store import Store
from tests.conftest import make_pdf


def test_ingest_dir_skips_unchanged_and_counts_failures(tmp_path: Path, store: Store) -> None:
    make_pdf(tmp_path / "a.pdf")
    (tmp_path / "sub").mkdir()
    make_pdf(tmp_path / "sub" / "b.pdf")
    (tmp_path / "bad.pdf").write_bytes(b"nope")

    r1 = ingest_dir(tmp_path, store)
    assert (r1.ingested, r1.skipped, r1.failed) == (2, 0, 1)
    r2 = ingest_dir(tmp_path, store)
    assert (r2.ingested, r2.skipped) == (0, 2)
    r3 = ingest_dir(tmp_path, store, force=True)
    assert r3.ingested == 2


def test_changed_file_is_reingested(tmp_path: Path, store: Store) -> None:
    p = make_pdf(tmp_path / "a.pdf", ["original text"])
    ingest_file(p, store)
    make_pdf(p, ["completely different"])
    assert ingest_file(p, store) >= 1
    assert store.search("original") == []


def test_report(populated: Store) -> None:
    df = stats_frame(populated)
    assert df.height == 1 and df["pages"][0] == 2
    t = totals(df)
    assert t["documents"] == 1 and t["words"] > 10
    assert totals(stats_frame(Store(":memory:")))["documents"] == 0
