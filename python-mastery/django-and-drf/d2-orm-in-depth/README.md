# D2 — The ORM in depth

D1 used the ORM the way tutorials do. D2 is where you learn what SQL it sends and when, and how to make it send less. Most production Django performance bugs are ORM bugs. Most production Django data-integrity bugs are transaction bugs. Both are here.

**Rule for all of D2:** keep SQL logging on while you work. Add this to the bottom of `config/settings.py` for the duration of D2:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django.db.backends": {"handlers": ["console"], "level": "DEBUG"}},
}
```

`runserver` then prints every query (only while `DEBUG = True`). Reading those logs is a large part of what this project teaches.

## Steps

| Step | File | You build | Checkpoint |
|---|---|---|---|
| 1 | [01-querysets.md](01-querysets.md) | `IssueQuerySet` with `open()` and `visible_to()`; your first own tests | `test_d2_01_querysets.py` |
| 2 | [02-n-plus-one.md](02-n-plus-one.md) | Labels; a project page whose query count doesn't grow with issues | `test_d2_02_n_plus_one.py` |
| 3 | [03-aggregation.md](03-aggregation.md) | A dashboard of per-project counts and last activity | `test_d2_03_aggregation.py` |
| 4 | [04-transactions.md](04-transactions.md) | A race-free `create_issue` service; a tested data migration | `test_d2_04_transactions.py` |

## Done means

- `uv run pytest ../checkpoints/d1 ../checkpoints/d2` is green. D2 must not break D1.
- You have at least five tests of your own in `trackr/tests/`.
- `NOTES.md`: every "Explain it back" answer, plus a one-page "ORM cheat sheet in my own words". Cover when each of `select_related`, `prefetch_related`, `annotate`, `aggregate`, `Subquery`, `F` and `select_for_update` is the right tool, with one example each from trackr.
