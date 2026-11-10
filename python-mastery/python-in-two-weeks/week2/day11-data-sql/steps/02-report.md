# Step 2 — A polars report

**Checkpoint:** `uv run pytest ../checkpoints`

## Concepts

`copy/01_polars.py` was expressions on a frame you already had. Here the frame is a list of note dicts from the repo:

- one row per tag, then `group_by("tag").len()`
- one row per note, with the calendar day taken from the first 10 characters of `created_at`, then `group_by("day").len()`

`group_by().len()` names the count column `"len"`. Cast each count with `int(...)` so you return plain Python ints, not polars scalars.

An empty input returns `{"per_tag": {}, "per_day": {}}` without building a frame. A note with no tags still counts for its day and adds nothing to `per_tag`.

## Your turn

```python
def summarise(notes: list[dict]) -> dict[str, dict[str, int]]: ...
```

Export it from `notesql`.

Sort the keys (polars `sort` before you turn the columns into a dict) so the result doesn't depend on hash order.

## Checkpoint

```bash
uv run pytest ../checkpoints
```

## Finish

1. Both checkpoints pass.
2. Answer the questions in `NOTES.md`.
3. Only then open `reference/notesql/` and diff it. Write down which version you'd keep.

Wire `SqliteRepo` into Day 10 by implementing the `NoteRepo` protocol and overriding `get_repo` in tests with `SqliteRepo(":memory:")`. That's the original build task; the checkpoints above are the part you can prove without the FastAPI app running.
