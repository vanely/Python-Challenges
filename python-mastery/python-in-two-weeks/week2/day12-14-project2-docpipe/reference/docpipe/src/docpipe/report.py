"""Stats via polars."""

from __future__ import annotations

import polars as pl

from docpipe.store import Store


def stats_frame(store: Store) -> pl.DataFrame:
    rows = store.stats_rows()
    if not rows:
        return pl.DataFrame(
            schema={
                "path": pl.Utf8,
                "pages": pl.Int64,
                "chunks": pl.Int64,
                "words": pl.Int64,
                "words_per_page": pl.Float64,
            }
        )
    return (
        pl.DataFrame(rows)
        .with_columns(
            path=pl.col("path").str.split("/").list.last(),
            words_per_page=(pl.col("words") / pl.col("pages").clip(1)).round(1),
        )
        .select("path", "pages", "chunks", "words", "words_per_page")
    )


def totals(df: pl.DataFrame) -> dict[str, int]:
    if df.is_empty():
        return {"documents": 0, "pages": 0, "chunks": 0, "words": 0}
    return {
        "documents": df.height,
        "pages": int(df["pages"].sum()),
        "chunks": int(df["chunks"].sum()),
        "words": int(df["words"].sum()),
    }
