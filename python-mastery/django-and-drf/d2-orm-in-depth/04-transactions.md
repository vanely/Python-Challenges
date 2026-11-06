# D2.04 — Transactions, row locks, services, and a tested data migration

**Time:** ~3 h · **Checkpoint:** `uv run pytest ../checkpoints/d2/test_d2_04_transactions.py`

## What you'll have at the end

- A `tracker/services.py` with `create_issue` and `create_project`. Both are atomic, and `create_issue` is race-free under concurrent requests on PostgreSQL.
- A per-project counter column, populated for existing data by a data migration you've tested going forwards.
- The views calling the services instead of doing the work inline.

## Concepts

### Autocommit, and what `atomic` changes

By default Django runs in **autocommit**: every query is its own transaction, committed immediately. So in D1.05's view:

```python
last = project.issues.order_by("-number").first()   # transaction 1
issue.number = last.number + 1
issue.save()                                          # transaction 2
form.save_m2m()                                       # transaction 3
```

If `save_m2m()` fails, the issue exists without its labels. Partial writes like that are how data rots.

`transaction.atomic` groups work into one transaction: all of it commits, or none of it does.

```python
from django.db import transaction

with transaction.atomic():
    ...   # BEGIN ... COMMIT, or ROLLBACK if an exception escapes the block
```

- It works as a decorator (`@transaction.atomic`) or a context manager.
- **Nesting** creates *savepoints*: an inner `atomic()` that fails rolls back to its savepoint, and the outer block can catch the exception and continue. That's why D1.02's tests wrap the expected `IntegrityError` in `atomic()`. On PostgreSQL, an error *without* a savepoint aborts the whole outer transaction, and every later query fails with "current transaction is aborted".
- **Never catch database errors *inside* an atomic block** to "keep going". Catch them *outside* it, or around an inner `atomic()`.
- `transaction.on_commit(fn)` runs `fn` after the outermost transaction commits. Use it for side effects that must not happen if the write rolls back: sending email, enqueueing a background task.
- `ATOMIC_REQUESTS = True` (a per-database setting) wraps every view in a transaction. It's simple, but it holds a transaction open for the whole request, including slow template rendering. Explicit `atomic` around the write is usually better.

### The numbering race, and why atomic alone doesn't fix it

Wrap D1.05's logic in `atomic()` and replay the race on PostgreSQL's default isolation (READ COMMITTED):

| Time | Request A | Request B |
|---|---|---|
| t1 | BEGIN; read max → 4 | |
| t2 | | BEGIN; read max → 4 (A hasn't committed) |
| t3 | INSERT #5; COMMIT | |
| t4 | | INSERT #5 → **IntegrityError** |

Transactions make work *atomic*. They don't make it *serial*. Two transactions can still read the same "current" value. You need one of:
1. **Retry on conflict.** Catch the `IntegrityError` and try again. It works, and it's ugly under load.
2. **Lock something both requests must touch.** `SELECT … FOR UPDATE` on the project row: the second request **blocks** at its read until the first commits, then reads the new value.
3. **Let the database do the arithmetic in one statement.** `UPDATE … SET n = n + 1 RETURNING n`. Django's `update()` doesn't return values, so in Django you'd use raw SQL for this.

This step uses option 2 with a counter column on `Project`:

```python
@transaction.atomic
def create_issue(*, project, reporter, title, labels=(), **fields):
    locked = Project.objects.select_for_update().get(pk=project.pk)   # SELECT ... FOR UPDATE
    number = locked.next_issue_number
    locked.next_issue_number = number + 1
    locked.save(update_fields=["next_issue_number"])
    issue = Issue.objects.create(project=locked, number=number, reporter=reporter, title=title, **fields)
    if labels:
        issue.labels.set(labels)
    return issue
```

- **`select_for_update()` only works inside a transaction.** The lock is released at COMMIT or ROLLBACK, and outside `atomic` there's nothing to hold it. On PostgreSQL, MySQL and Oracle, Django raises `TransactionManagementError` if you try. On SQLite it's silently ignored (see below), so a missing `atomic` won't show up in your SQLite tests.
- **Why a counter instead of locking and then `MAX(number)`?** Both work under the lock. The counter is O(1) instead of an aggregate. It also never reuses a number, even if the newest issue is deleted, which matches how GitHub behaves.
- **`update_fields`** writes only that column, so this `save()` can't overwrite concurrent changes to the project's name or description.
- The **unique constraint stays** as the last line of defence. Locks are a correctness *mechanism*; constraints are the *guarantee*.

### SQLite is different (and why that matters for your tests)

SQLite has no row locks: `select_for_update()` is silently ignored there. Instead, SQLite allows **one writer for the whole database at a time**. With Django's default `DEFERRED` transactions, two requests can both read, then both try to write. One of them gets `database is locked` instead of waiting its turn.

Django ≥ 5.1 lets you choose `BEGIN IMMEDIATE`, which takes the write lock at the start of every `atomic()` block, so concurrent writers queue up instead of failing:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"transaction_mode": "IMMEDIATE"},
    }
}
```

The lesson generalises: **concurrency behaviour is a property of the database, not of Django.** Your tests run on SQLite, so they can check that your code is *atomic*, but not that it's *race-free* on PostgreSQL. Teams that care run their test suite on the production database engine. Stage 3 Tier 3 has you build concurrency tests that actually race.

### Where business logic lives: services

`create_issue` touches two tables, holds a lock, and enforces a numbering rule. Where should it go?
- **In the view?** Then the API (R1) duplicates it, and so does the next management command.
- **In `Issue.save()`?** Then every `save()`, including edits, has to reason about numbering and locks, and `bulk_create` skips it entirely.
- **In a signal?** Even more invisible. Signals are for decoupling *apps*, not for hiding your own app's core logic.
- **A plain function in `services.py`**, called by views, API, admin actions and scripts alike. Keyword-only arguments make every call site self-documenting.

This is the most common shape in mature Django codebases. Use model methods for logic about *one instance* (`issue.close()`) and services for *workflows* that span rows and transactions.

### Data migrations

Adding `next_issue_number` with `default=1` is a schema migration. But existing projects already have issues, so their counter must start at `max(number) + 1`, not 1. That's a **data migration**, a `RunPython` operation:

```python
def backfill(apps, schema_editor):
    Project = apps.get_model("tracker", "Project")
    ...

class Migration(migrations.Migration):
    dependencies = [("tracker", "000N_project_next_issue_number")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
```

- **`apps.get_model`, never `from tracker.models import Project`.** A migration must run against the schema *as it was at that point in history*. Your current model class might have fields that don't exist yet when this migration runs on an old database. `apps` gives you a historical model built from the migration state, with fields but no custom methods or managers.
- **The reverse function**: `RunPython.noop` declares "nothing to undo", so you can migrate backwards past it. Without a reverse function the migration is irreversible.
- **Test it.** The checkpoint does what a careful team does: migrate to just before your migration, insert data using the *historical* models, migrate forward, and assert. Read `test_backfill_migration` in the checkpoint file. You'll reuse that pattern.

## Build

### 1. Settings

Add `"OPTIONS": {"transaction_mode": "IMMEDIATE"}` to the SQLite database config, as above.

### 2. The counter column (schema migration)

On `Project`:

```python
    next_issue_number = models.PositiveIntegerField(default=1)
```

```bash
uv run python manage.py makemigrations tracker -n project_next_issue_number
```

### 3. Your turn: the data migration

```bash
uv run python manage.py makemigrations tracker --empty -n backfill_next_issue_number
```

Fill in the generated file so that every existing project's `next_issue_number` becomes one more than its highest issue number, or stays 1 if it has no issues. Make it reversible with a no-op reverse.

<details><summary>Hint 1</summary>

One query can compute every project's max: `annotate(max_number=Max("issues__number"))` on the historical `Project`. `Max` over no rows is `None`.
</details>

<details><summary>Hint 2</summary>

Save with `update_fields=[...]`. Historical models have no custom `save()` logic, but there's no reason to write every column.
</details>

Before migrating, make sure your dev database has a project with some issues. Then:

```bash
uv run python manage.py migrate
uv run python manage.py shell -c "from tracker.models import Project; print([(p.slug, p.next_issue_number) for p in Project.objects.all()])"
```

### 4. The services

Create `tracker/services.py`:

```python
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.db import transaction

from .models import Issue, Label, Membership, Project

if TYPE_CHECKING:
    from accounts.models import User


@transaction.atomic
def create_issue(
    *,
    project: Project,
    reporter: User,
    title: str,
    labels: Iterable[Label] = (),
    **fields: Any,
) -> Issue:
    locked = Project.objects.select_for_update().get(pk=project.pk)
    number = locked.next_issue_number
    locked.next_issue_number = number + 1
    locked.save(update_fields=["next_issue_number"])

    issue = Issue.objects.create(
        project=locked, number=number, reporter=reporter, title=title, **fields
    )
    if labels:
        issue.labels.set(labels)
    return issue
```

`TYPE_CHECKING` is `False` at runtime. The import only exists for type checkers, which avoids importing `accounts.models` from `tracker` at module load. That's a habit that prevents circular imports between apps.

**Your turn:** add `create_project(*, owner, name, slug, description="") -> Project`. It atomically creates the project *and* the owner's `admin` membership. A project with no admin membership must be impossible to create through this function. R1 uses it.

### 5. Use the service in the view

```python
from .services import create_issue

@login_required
def issue_create(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(member_projects(request), slug=slug)
    if request.method == "POST":
        form = IssueForm(request.POST, project=project)
        if form.is_valid():
            issue = create_issue(project=project, reporter=request.user, **form.cleaned_data)
            return redirect(issue)
    else:
        form = IssueForm(project=project)
    return render(request, "tracker/issue_form.html", {"form": form, "project": project})
```

`form.cleaned_data` has exactly the keys in `IssueForm.Meta.fields`: `title`, `body`, `priority`, `assignee`, and `labels` as a QuerySet. They line up with the service's parameters. The form validates; the service writes. `form.save()` isn't used for creation any more, so the `save_m2m()` trap is gone.

Also deal with the admin. Its add form has never been able to create issues: `number` is read-only there, so it fails with the `NOT NULL` error you saw in D1.03. Anything created there now should go through the service too. Either make the admin's add form unavailable (`has_add_permission` returning `False`), or override `IssueAdmin.save_model` to call the service for new objects. Pick one and justify it in `NOTES.md`.

## Checkpoint

```bash
uv run pytest ../checkpoints/d2/test_d2_04_transactions.py
uv run pytest ../checkpoints/d1 ../checkpoints/d2      # everything so far
```

The migration test uses `@pytest.mark.django_db(transaction=True)`. Migrations can't run inside the rolled-back test transaction, so this test uses real commits and a flush afterwards. That's why it's slower.

## Pitfalls

- **`select_for_update()` outside `atomic`**: `TransactionManagementError` on PostgreSQL, silently no locking on SQLite. Your SQLite tests won't catch this one.
- **Locking, then doing slow work (HTTP calls, emails) inside the transaction.** Every other creator in that project waits. Keep the locked section short, and push side effects to `transaction.on_commit`.
- **Importing real models in a migration.** It works today and breaks the day the model changes.
- **Catching `IntegrityError` inside `atomic()` and carrying on.** On PostgreSQL the transaction is already aborted.
- **Believing SQLite tests prove concurrency safety.** They prove atomicity only.

## Explain it back

1. Replay the race table with `select_for_update` in place. At which exact point does request B wait, and what value does it read when it resumes?
2. Why does a lock require a transaction? Why can't your test suite tell you that you forgot the `atomic`?
3. What does `transaction_mode: IMMEDIATE` change on SQLite, and what does it cost?
4. Why must a data migration use `apps.get_model`? Describe a concrete future change that would break a migration that imported `tracker.models.Project`.
5. D2 retrospective: what's the most expensive ORM mistake you made or nearly made in D1, now that you can see the SQL?

## Read the source (optional)

`django/db/transaction.py`, class `Atomic`: `__enter__` and `__exit__`. The savepoint logic is about 100 lines and explains every nesting behaviour above.
