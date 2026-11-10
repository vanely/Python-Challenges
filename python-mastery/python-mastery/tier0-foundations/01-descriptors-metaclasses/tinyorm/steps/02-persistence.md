# Step 2 — Insert, update, identity

**Checkpoint:** from `student/`, `uv run pytest ../checkpoints/test_orm.py -k "save_insert or eq_and_hash or fields or descriptor or class_access or manager or does_not_exist"`

## What has to be true

- `save()` inserts when `pk` is `None` and updates otherwise. The insert stores the new id on the instance.
- `refresh_from_db()` reloads columns. `delete()` removes the row and clears `pk`.
- `objects.create(...)` is a shortcut that constructs and saves.
- `__eq__` and `__hash__` use `(type, pk)`. An unsaved instance is unhashable (`TypeError`).
- Two instances with the same pk compare equal even if you loaded one of them again.

## Explain it back

1. Why is an unsaved instance unhashable?
2. Where does `lastrowid` come from, and when is it `None`?
