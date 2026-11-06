# R2 — The production API

R1's API works. R2 makes it something you could put in front of real clients:
- **fast**, because its cost doesn't grow with page size;
- **consistent**, with one error shape for every failure;
- **defended**, with throttles where credential stuffing happens;
- **documented**, with an OpenAPI schema that validates in CI;
- **deployable**, with settings from the environment and a clean `check --deploy`.

## Steps

| Step | File | You build | Checkpoint |
|---|---|---|---|
| 1 | [01-performance.md](01-performance.md) | Query-budget tests; open-issue counts computed in SQL | `test_r2_01_performance.py` |
| 2 | [02-errors-throttling-schema.md](02-errors-throttling-schema.md) | Error envelope, throttled login, OpenAPI + Swagger UI | `test_r2_02_errors_schema.py` |
| 3 | [03-production-settings.md](03-production-settings.md) | Environment-driven settings, secure defaults, `check --deploy` passing | `test_r2_03_production.py` |

## Done means

- `uv run pytest ../checkpoints` is entirely green: D1, D2, R1 and R2.
- `uv run ruff check .` is clean.
- `NOTES.md` has every answer, plus the Stage 2 retrospective at the end of R2.03.

Then go to Stage 3, `../../python-mastery/`. Tier 0.1 opens Django's `ModelBase` and shows you how everything you've used in this stage is built.
