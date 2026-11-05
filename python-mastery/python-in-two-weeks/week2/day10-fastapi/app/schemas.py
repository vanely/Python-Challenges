"""Pydantic models = the API contract. Validation happens at the boundary."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unknown keys, like zod .strict()

    title: str = Field(min_length=1, max_length=120)
    body: str = ""
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("tags")
    @classmethod
    def normalise_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t.strip()})


class NoteUpdate(BaseModel):
    """PATCH shape: every field optional; use model_dump(exclude_unset=True)."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = None
    tags: list[str] | None = None


class NoteOut(NoteIn):
    id: int
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


def now() -> datetime:
    return datetime.now(UTC)
