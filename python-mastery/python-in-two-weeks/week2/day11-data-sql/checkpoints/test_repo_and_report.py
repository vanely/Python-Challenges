"""Day 11: SQLite repo and the polars report. Spec: steps/01-sqlite-repo.md, steps/02-report.md."""

from __future__ import annotations

import pytest

from notesql import NoteNotFound, SqliteRepo, summarise


def test_create_get_normalises_tags() -> None:
    repo = SqliteRepo()
    note = repo.create("Hi", body="b", tags=[" B ", "a", "b", ""])
    assert note["tags"] == ["a", "b"]
    assert note["title"] == "Hi" and note["body"] == "b"
    assert repo.get(note["id"])["tags"] == ["a", "b"]
    repo.close()


def test_list_filters_and_pages() -> None:
    repo = SqliteRepo()
    for i in range(5):
        repo.create(str(i), tags=["even" if i % 2 == 0 else "odd"])
    page, total = repo.list(limit=2, offset=1, tag="even")
    assert total == 3 and len(page) == 2
    assert [n["title"] for n in page] == ["2", "4"]
    repo.close()


def test_update_delete_and_missing() -> None:
    repo = SqliteRepo()
    note = repo.create("t", body="b", tags=["a"])
    updated = repo.update(note["id"], {"body": "changed"})
    assert updated["title"] == "t" and updated["body"] == "changed" and updated["tags"] == ["a"]
    retagged = repo.update(note["id"], {"tags": ["Z", "z"]})
    assert retagged["tags"] == ["z"]
    repo.delete(note["id"])
    with pytest.raises(NoteNotFound):
        repo.get(note["id"])
    repo.close()


def test_delete_removes_tags() -> None:
    repo = SqliteRepo()
    note = repo.create("t", tags=["a"])
    repo.delete(note["id"])
    assert repo.list(limit=10, offset=0, tag="a")[1] == 0
    repo.close()


def test_summarise_groups_in_polars() -> None:
    notes = [
        {"tags": ["a", "b"], "created_at": "2026-11-01T10:00:00+00:00"},
        {"tags": ["a"], "created_at": "2026-11-01T18:00:00+00:00"},
        {"tags": [], "created_at": "2026-11-02T01:00:00+00:00"},
    ]
    out = summarise(notes)
    assert out["per_tag"] == {"a": 2, "b": 1}
    assert out["per_day"] == {"2026-11-01": 2, "2026-11-02": 1}
    assert summarise([]) == {"per_tag": {}, "per_day": {}}
