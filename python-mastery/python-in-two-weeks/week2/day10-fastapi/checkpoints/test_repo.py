"""Step 1: the in-memory repo. Spec: steps/01-schemas-and-repo.md."""

from __future__ import annotations

import pytest

from app.repo import MemoryRepo, NoteNotFound
from app.schemas import NoteIn


def test_create_normalises_tags_and_roundtrips() -> None:
    repo = MemoryRepo()
    note = repo.create(NoteIn(title="Hi", tags=[" B ", "a", "b", ""]))
    assert note.tags == ["a", "b"]
    assert note.title == "Hi" and note.id == 1
    page, total = repo.list(limit=10, offset=0, tag="a")
    assert total == 1 and page[0].id == note.id
    updated = repo.update(note.id, {"body": "x"})
    assert updated.title == "Hi" and updated.body == "x" and updated.tags == ["a", "b"]
    repo.delete(note.id)
    with pytest.raises(NoteNotFound) as exc:
        repo.get(note.id)
    assert exc.value.note_id == note.id
