"""Polars summaries over notes the store already loaded."""

from __future__ import annotations

from typing import Any

import polars as pl


def summarise(notes: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Notes per tag, and notes per calendar day (the date prefix of created_at)."""
    if not notes:
        return {"per_tag": {}, "per_day": {}}
    tag_rows = [{"tag": tag} for note in notes for tag in note["tags"]]
    day_rows = [{"day": str(note["created_at"])[:10]} for note in notes]
    return {"per_tag": _counts(tag_rows, "tag"), "per_day": _counts(day_rows, "day")}


def _counts(rows: list[dict[str, str]], column: str) -> dict[str, int]:
    if not rows:
        return {}
    frame = pl.DataFrame(rows).group_by(column).len().sort(column)
    keys = frame[column].to_list()
    counts = frame["len"].to_list()
    return {key: int(n) for key, n in zip(keys, counts, strict=True)}
