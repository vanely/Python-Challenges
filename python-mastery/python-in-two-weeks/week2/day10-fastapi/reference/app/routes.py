from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.deps import Repo
from app.schemas import NoteIn, NoteOut, NoteUpdate, Page
from app.settings import settings

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("")
def list_notes(
    repo: Repo,
    limit: Annotated[int, Query(ge=1, le=settings.max_page)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    tag: str | None = None,
) -> Page[NoteOut]:
    items, total = repo.list(limit=limit, offset=offset, tag=tag)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_note(data: NoteIn, repo: Repo) -> NoteOut:
    return repo.create(data)


@router.get("/{note_id}")
def get_note(note_id: int, repo: Repo) -> NoteOut:
    return repo.get(note_id)


@router.patch("/{note_id}")
def update_note(note_id: int, data: NoteUpdate, repo: Repo) -> NoteOut:
    try:
        return repo.update(note_id, data.model_dump(exclude_unset=True))
    except ValidationError as e:  # re-validation in the repo; only RequestValidationError → 422
        raise RequestValidationError(e.errors()) from e


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, repo: Repo) -> None:
    repo.delete(note_id)
