"""Internal records are dataclasses; API-boundary records are Pydantic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class Page:
    number: int  # 1-based
    text: str


@dataclass(frozen=True, slots=True)
class Chunk:
    page_no: int
    index: int  # position within the document
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True, slots=True)
class Document:
    id: int
    path: str
    sha256: str
    pages: int
    ingested_at: datetime


@dataclass(slots=True)
class IngestReport:
    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    chunks: int = 0
    seconds: float = 0.0


class SearchHit(BaseModel):
    document_id: int
    path: str
    page_no: int
    chunk_index: int
    score: float = Field(description="Lower is better (bm25)")
    snippet: str


class DocumentOut(BaseModel):
    id: int
    path: str
    pages: int
    chunks: int
    ingested_at: datetime
