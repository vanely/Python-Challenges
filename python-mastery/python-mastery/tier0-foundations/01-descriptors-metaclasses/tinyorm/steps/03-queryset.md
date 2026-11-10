# Step 3 — The lazy QuerySet

**Checkpoint:** from `student/`, `uv run pytest ../checkpoints/test_orm.py`

## What has to be true

The checkpoint's `Product` is in `checkpoints/conftest.py`. Read it. Your ORM has to accept that model, including an abstract `Timestamped` base.

- `filter` / `exclude` / `order_by` return a new QuerySet. Nothing hits SQLite until iteration, `len`, `count`, `exists`, `get`, `first`, slicing that evaluates, `update`, or `delete`.
- Results cache on the QuerySet. Iterating twice issues one query. `Database.log` is how the tests see that.
- Lookups: exact, `gt`/`gte`/`lt`/`lte`, `contains`, `startswith`, `in` (including an empty list), `isnull`, and `pk`.
- Slicing compiles to `LIMIT`/`OFFSET`. Further slicing composes with the slice you already had. An index past the slice raises `IndexError`. `count` and `exists` honour the slice.
- `get` raises `MultipleObjectsReturned` when several rows match, and `Product.DoesNotExist` when none do.
- An unknown field name raises `ValueError`.
- `update` validates values and returns the row count. `delete` returns the row count. `values("id", "name")` returns a list of dicts.

## Finish

`uv run pytest ../checkpoints` from `student/`, then `uv run mypy src` and `uv run ruff check .`. Answer the questions in the stage `NOTES.md`. Open `reference/tinyorm/` only after that, and write down one thing the reference does that you didn't.

## Explain it back

1. Why is the SQL string still using `?` when the lookup name itself was built dynamically?
2. What breaks if `filter` mutates `self` instead of returning a new QuerySet?
