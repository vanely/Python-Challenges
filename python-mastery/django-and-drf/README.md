# Stage 2 — Django and Django REST Framework, as guided projects

Stage 2 of the [roadmap](../README.md). You finished Stage 1 (`../python-in-two-weeks/`): you can write typed, idiomatic Python and you've built a FastAPI service. This stage teaches the framework most Python backend jobs actually use, and it is the stage Stage 3 (`../python-mastery/`) assumes you've done. Tier 0.1 there opens with "you've used `class Article(models.Model)` a thousand times"; after this stage, that's true.

You build **one** codebase, `trackr`, an issue tracker, across four guided projects. Each step explains the mechanism first, then has you build it, then checks you with tests you didn't write.

| Project | What you build | What you learn | Time |
|---|---|---|---|
| [D1 — Django core](d1-django-core/README.md) | Server-rendered issue tracker: models, admin, views, templates, forms, auth, class-based views | The request/response cycle, the ORM's shape, migrations, the admin, CSRF, scoping data to a user | ~12 h |
| [D2 — The ORM in depth](d2-orm-in-depth/README.md) | Custom QuerySets, a constant-query project page, a dashboard of aggregates, a race-free numbering service | Laziness, N+1, `select_related`/`prefetch_related`, `annotate`/`aggregate`, join fan-out, subqueries, transactions, row locks, data migrations | ~10 h |
| [R1 — DRF fundamentals](r1-drf-fundamentals/README.md) | A JSON API over the same models: projects, nested issues, actions, filtering | Serializers, ViewSets, routers, authentication vs permissions, object-level permissions, scoped relations | ~12 h |
| [R2 — Production API](r2-production-api/README.md) | The same API made fast, consistent, documented, and deployable | Query budgets in APIs, error envelopes, throttling, OpenAPI, environment-driven settings, `check --deploy` | ~8 h |

At ~8–10 hrs/week that's 5–6 weeks. If a step takes twice as long as its estimate, that's normal. Don't skip the "Explain it back" questions to catch up.

## How a guided step works

Every step file has the same sections:

1. **Concepts.** The mechanism, explained properly: what Django does, in what order, and why. Read this before touching code.
2. **Build.** Code to type (not paste) with commentary. Typing it is how you notice the details.
3. **Your turn.** A piece specified in prose with hints but **no code**. The checkpoint tests check it. This is where most of the learning happens, so don't look up a solution.
4. **Checkpoint.** A test file in `checkpoints/` that you run against your code. Green means you can move on. The tests are the spec; read them when you're stuck. Don't edit them.
5. **Pitfalls.** The mistakes people actually make with this feature.
6. **Explain it back.** Questions to answer in writing in `NOTES.md` at the root of this folder. If you can't answer one without re-reading, re-read the Concepts section. Don't start the next step until they're answered.

There is no finished `trackr` to copy from. The guides and the checkpoints are the reference.

## Setup (once)

From this folder (`python-mastery/django-and-drf/`), in Git Bash:

```bash
uv sync                      # creates .venv with Python 3.12, Django 6.1, DRF 3.18, pytest-django
uv run python --version      # Python 3.12.x
uv run django-admin --version
```

You never need to activate the virtualenv; `uv run <cmd>` runs inside it. Commands in the guides are run from `trackr/` once it exists (D1.01 creates it). `uv` finds `pyproject.toml` in the parent folder automatically.

Run a checkpoint from `trackr/`:

```bash
uv run pytest ../checkpoints/d1/test_d1_01_setup.py
```

Run all checkpoints for a finished project, to make sure later work didn't break earlier steps:

```bash
uv run pytest ../checkpoints/d1 ../checkpoints/d2
```

## Versions and why they matter

- **Python 3.12.** Django 6.x requires ≥ 3.12.
- **Django 6.1.** Newer than most tutorials online. Differences you'll actually hit: email is configured with the `MAILERS` setting (the old `EMAIL_*` settings are deprecated), `CheckConstraint` takes `condition=` (not `check=`), and `DEFAULT_AUTO_FIELD` already defaults to `BigAutoField`. When a blog post disagrees with these guides, check the [6.1 docs](https://docs.djangoproject.com/en/6.1/).
- **DRF 3.18**, **django-filter 26**, **drf-spectacular 0.30**.

## Typing in this stage

Stage 1's rule was "`mypy --strict` passes before anything is done." Django is the exception. The ORM builds attributes at class-creation time (Stage 3 Tier 0.1 shows you exactly how), so plain mypy can't see them. Full typing needs `django-stubs` and its mypy plugin. In this stage: annotate your function signatures, run `uv run ruff check`, and skip mypy. Adding `django-stubs` is an optional stretch at the end of R2.

## Primary sources

- Django docs, 6.1: https://docs.djangoproject.com/en/6.1/ — the tutorial (parts 1–5) is good but shallow; these guides go deeper on the parts that matter in production. "Topics → Models and databases" and "Topics → Handling HTTP requests" are worth reading in full during D1–D2.
- DRF: https://www.django-rest-framework.org/ — read "API Guide" pages as each step references them. Tom Christie's tutorial is the canonical intro.
- Classy CBV (https://ccbv.co.uk/) and Classy DRF (https://www.cdrf.co/) — every method of every generic view, flattened. You will use these constantly in D1.06 and R1.02.
- *Two Scoops of Django* (Feldroy) — opinionated project-structure advice; older editions are still mostly right.
- Django source: `django/db/models/`, `django/views/generic/`, `django/contrib/auth/`. Stage 3 sends you back here deliberately.
