"""Day 11 checked build: a SQLite note store and a polars report."""

from notesql.report import summarise
from notesql.repo import NoteNotFound, SqliteRepo

__all__ = ["NoteNotFound", "SqliteRepo", "summarise"]
