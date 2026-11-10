"""Dependency injection. FastAPI resolves these by annotation, like pytest fixtures."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.repo import MemoryRepo, NoteRepo

_repo = MemoryRepo()


def get_repo() -> NoteRepo:
    return _repo


Repo = Annotated[NoteRepo, Depends(get_repo)]
