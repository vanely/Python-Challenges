"""In-memory repository. Day 11 swaps this for SQLite behind the same interface."""

from __future__ import annotations

import itertools
from typing import Protocol

from app.schemas import NoteIn, NoteOut, now


class NoteNotFound(Exception):
    def __init__(self, note_id: int) -> None:
        super().__init__(f"note {note_id} not found")
        self.note_id = note_id


class NoteRepo(Protocol):
    """Structural interface: anything with these methods works."""

    def list(self, *, limit: int, offset: int, tag: str | None) -> tuple[list[NoteOut], int]: ...
    def get(self, note_id: int) -> NoteOut: ...
    def create(self, data: NoteIn) -> NoteOut: ...
    def update(self, note_id: int, changes: dict[str, object]) -> NoteOut: ...
    def delete(self, note_id: int) -> None: ...


class MemoryRepo:
    def __init__(self) -> None:
        self._notes: dict[int, NoteOut] = {}
        self._ids = itertools.count(1)

    def list(self, *, limit: int, offset: int, tag: str | None) -> tuple[list[NoteOut], int]:
        notes = [n for n in self._notes.values() if tag is None or tag in n.tags]
        return notes[offset : offset + limit], len(notes)

    def get(self, note_id: int) -> NoteOut:
        try:
            return self._notes[note_id]
        except KeyError:
            raise NoteNotFound(note_id) from None

    def create(self, data: NoteIn) -> NoteOut:
        note = NoteOut(id=next(self._ids), created_at=now(), **data.model_dump())
        self._notes[note.id] = note
        return note

    def update(self, note_id: int, changes: dict[str, object]) -> NoteOut:
        current = self.get(note_id)
        updated = current.model_copy(update=changes)
        # re-validate through NoteIn so tag normalisation runs
        validated = NoteIn.model_validate(updated.model_dump(include={"title", "body", "tags"}))
        note = NoteOut(id=current.id, created_at=current.created_at, **validated.model_dump())
        self._notes[note_id] = note
        return note

    def delete(self, note_id: int) -> None:
        self.get(note_id)
        del self._notes[note_id]
