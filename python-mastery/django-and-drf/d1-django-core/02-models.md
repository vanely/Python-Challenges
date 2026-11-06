# D1.02 — Models, relationships, and invariants the database enforces

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/d1/test_d1_02_models.py`

## What you'll have at the end

`Project`, `Membership`, `Issue` and `Comment` models with:
- the right foreign-key delete behaviour;
- choices for status and priority;
- uniqueness and check constraints *in the database*;
- two small model methods that keep an invariant.

## Concepts

### A model is a class, a table, and a query API

```python
class Project(models.Model):
    name = models.CharField(max_length=100)
```

That declaration does three jobs:
- it describes a table (`tracker_project` with a `name varchar(100)` column);
- it gives instances attribute access (`project.name`);
- it gives the class a manager (`Project.objects`) that builds SQL.

How a class attribute `name = CharField(...)` becomes a per-instance value is *descriptors and a metaclass*. Stage 3 Tier 0.1 has you rebuild that machinery. For now, trust it.

Every model gets an auto-incrementing primary key `id` (a `BigAutoField`, the default in Django 6) unless you declare one.

### Relationships

| Field | Cardinality | Column | Reverse accessor |
|---|---|---|---|
| `ForeignKey(Project)` on `Issue` | many issues → one project | `project_id` on `tracker_issue` | `project.issue_set` or, with `related_name="issues"`, `project.issues` |
| `ManyToManyField(User, through=Membership)` | many ↔ many | none on either table; rows live in `tracker_membership` | `user.projects` (`related_name`) |
| `OneToOneField` | one ↔ one | unique FK column | `user.profile` |

**Always set `related_name`.** `project.issues.all()` reads better than `project.issue_set.all()`. More importantly, two foreign keys from the same model to the same target (`reporter` and `assignee`, both pointing at `User`) *must* have distinct reverse names, or Django refuses to start.

**`through=` models.** A plain `ManyToManyField` creates a hidden join table with two columns. As soon as the relationship has data of its own (a role, a join date), make the join table a real model and name it with `through=`. You'll then create memberships with `Membership.objects.create(...)`. In Django ≥ 2.2 you can also use `project.members.add(user, through_defaults={"role": "admin"})`.

### `on_delete` is a business decision

When a referenced row is deleted, what happens to rows pointing at it?

| Option | Meaning | Used here for |
|---|---|---|
| `CASCADE` | delete them too | issues when their project is deleted; comments with their issue |
| `PROTECT` | refuse; raise `ProtectedError` | a user who reported issues can't be deleted (deactivate them instead with `is_active=False`) |
| `SET_NULL` | null the FK (requires `null=True`) | the assignee leaves, so the issue becomes unassigned |
| `RESTRICT` | like PROTECT, but allows deletion if it's part of a cascade from elsewhere | rarely needed |

Django implements these **in Python**, in its `Collector`, not as database `ON DELETE` clauses. Deleting through the ORM respects them; a raw SQL `DELETE` doesn't. The upside is that Python-side cascades send `pre_delete`/`post_delete` signals and work on every database. The downside is that deleting a project with 50,000 issues can mean fetching those rows into Python first. Django skips the fetch ("fast delete") only when nothing cascades further from them and no delete signals are connected.

Django 6.1 added database-level alternatives: `models.DB_CASCADE`, `models.DB_SET_NULL` and `models.DB_SET_DEFAULT`. They emit a real `ON DELETE` clause and skip the Collector, so they're fast, but signals don't fire for the cascaded rows. Use the Python versions in this project. Remember the database ones exist for big tables.

### `null` vs `blank`

- `null=True`: the **database** column allows NULL.
- `blank=True`: **validation** (forms, `full_clean`) allows an empty value.

For strings, Django's convention is `blank=True` without `null=True`, with empty meaning `""`. That avoids having two different "empty" values. For an optional FK (`assignee`) you need both.

### Choices: `TextChoices` / `IntegerChoices`

```python
class Status(models.TextChoices):
    OPEN = "open", "Open"
```

Each member is a `str` (or `int`) enum: `Issue.Status.OPEN == "open"` is `True`. The second element is the human label. Django uses it for form widgets and `issue.get_status_display()`.

Choices are **not** a database constraint. The column is a plain `varchar`, and `Issue.objects.create(status="banana")` succeeds. Only `full_clean()` and forms enforce them. If the database must reject bad values, add a `CheckConstraint`.

### Constraints: put invariants where they can't be skipped

Validation in Python can be bypassed: by `QuerySet.update()`, by raw SQL, or by two processes racing. A database constraint can't. Django exposes two kinds in `Meta.constraints`:

```python
models.UniqueConstraint(fields=["project", "number"], name="unique_issue_number_per_project")
models.CheckConstraint(condition=Q(status="closed") | Q(closed_at__isnull=True), name="closed_at_only_when_closed")
```

- **Issue numbers** are unique *per project*, not globally. That makes it a composite unique constraint. (`unique=True` on `number` would be wrong: two projects can both have #1.)
- **`closed_at` may only be set if the issue is closed.** "Closed issues have a timestamp; open ones don't" is a fact about your data, so the database should hold you to it.

> Django 6 note: `CheckConstraint` takes `condition=`. Older tutorials use `check=`, which was deprecated in 5.1 and removed in 6.0.

Violations raise `django.db.IntegrityError` at `save()` time.

### Methods that maintain invariants

If closing an issue means "set status *and* timestamp", don't make every caller remember both. Give the model `close()` and `reopen()` methods and have callers use those. This is the start of a theme D2.04 finishes: **behaviour lives next to the data it protects.**

## Build

### 1. `tracker/models.py`

```python
from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Project(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_projects"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.project} ({self.role})"
```

Notes on what you just typed:
- `"Membership"` is a **string** reference, because the class doesn't exist yet when `Project` is defined. Django resolves it lazily.
- `auto_now_add=True` sets the value once, on insert. `auto_now=True` (used below for `updated_at`) sets it on *every* `save()`. Both make the field non-editable in forms.
- `SlugField` is a `CharField` with a slug validator (letters, numbers, hyphens, underscores) and a database index.
- `Meta.ordering` is the default `ORDER BY`. It's convenient, but it applies to *every* query on the model, including ones where you don't care about order. D2 shows its cost.

Now `Issue`:

```python
class Issue(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        CLOSED = "closed", "Closed"

    class Priority(models.IntegerChoices):
        LOW = 1, "Low"
        NORMAL = 2, "Normal"
        HIGH = 3, "High"
        URGENT = 4, "Urgent"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices, default=Priority.NORMAL
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_issues"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["project_id", "-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "number"], name="unique_issue_number_per_project"
            ),
            models.CheckConstraint(
                condition=Q(status="closed") | Q(closed_at__isnull=True),
                name="closed_at_only_when_closed",
            ),
        ]
        indexes = [models.Index(fields=["project", "status"])]

    def __str__(self) -> str:
        return f"#{self.number} {self.title}"

    def close(self, *, at: datetime | None = None) -> None:
        self.status = self.Status.CLOSED
        self.closed_at = at or timezone.now()

    def reopen(self) -> None:
        self.status = self.Status.OPEN
        self.closed_at = None
```

Why these choices:
- **`ordering = ["project_id", "-number"]`, not `["project", ...]`.** Ordering by the relation name `project` means "order by the *Project model's* default ordering", which is `name`. That forces a JOIN to the project table on every issue query. `project_id` orders by the raw column, with no join.
- **`indexes`.** The most common query will be "issues in project X with status Y". The unique constraint already indexes `(project, number)`; this index serves `(project, status)`. Indexes speed up reads, slow down writes, and cost disk. Add them for queries you *know* you run.
- **`close()` / `reopen()` don't call `save()`.** The caller decides when to persist, and may change other fields in the same write. D2 and R1 rely on that.
- **`timezone.now()`, never `datetime.now()`.** With `USE_TZ = True`, Django stores UTC and expects timezone-aware datetimes. A naive `datetime.now()` triggers a warning and is wrong whenever server time isn't UTC.

### 2. Your turn: `Comment`

Write the `Comment` model from this spec. No code is given.

- A comment belongs to one issue; deleting the issue deletes its comments. The reverse accessor is `issue.comments`.
- It has an author (a user). A user who has authored comments **cannot** be deleted. The reverse accessor is `user.comments`.
- `body` is required text of any length.
- `created_at` is set once on insert.
- Comments are ordered oldest first by default.
- `__str__` returns something readable.

<details><summary>Hint 1</summary>

The `on_delete` table above answers both delete questions. Compare `Comment.author` with `Issue.reporter`.
</details>

<details><summary>Hint 2</summary>

"Required text of any length" is a `TextField` *without* `blank=True`.
</details>

### 3. Make and inspect the migration

```bash
uv run python manage.py makemigrations tracker
uv run python manage.py sqlmigrate tracker 0001
uv run python manage.py migrate
```

Read the `sqlmigrate` output and find:
- the `UNIQUE` constraint;
- the `CHECK` constraint;
- the composite index;
- the `REFERENCES` clauses.

Notice that none of them say `ON DELETE CASCADE`: that's the Python-side `Collector` mentioned above. (Also notice SQLite migrations recreate the whole table as `new__tracker_issue` to add a constraint. SQLite's `ALTER TABLE` is limited, and Django works around it.)

### 4. Play in the shell

`uv run python manage.py shell` gives you a Python shell with Django configured. Since Django 5.2 it auto-imports your models.

```python
alice = User.objects.create_user("alice", password="pw")
p = Project.objects.create(name="Apollo", slug="apollo", owner=alice)
Membership.objects.create(project=p, user=alice, role="admin")
i = Issue.objects.create(project=p, number=1, title="Launch", reporter=alice)
p.issues.all()
alice.projects.all()
i.get_status_display()
Issue.objects.create(project=p, number=1, title="dup", reporter=alice)    # IntegrityError
```

## Checkpoint

```bash
uv run pytest ../checkpoints/d1/test_d1_02_models.py
```

The test file uses fixtures from `checkpoints/conftest.py` (`make_user`, `make_project`). Read them. They show the canonical way to create the objects you just modelled.

## Pitfalls

- **Forgetting `related_name` on two FKs to the same model.** Django refuses to start with error `fields.E304`.
- **`unique=True` on `number`.** It passes your own quick test and breaks as soon as a second project exists.
- **Catching `IntegrityError` without a transaction.** After an IntegrityError on PostgreSQL, the surrounding transaction is aborted and every later query fails. Wrap the risky write in `transaction.atomic()` (the checkpoint tests show the pattern). D2.04 explains why.
- **`auto_now` and `update()`.** `QuerySet.update()` bypasses `save()`, so `updated_at` is *not* bumped. Pass it explicitly when you bulk-update.

## Explain it back

1. For each FK in the schema, justify its `on_delete` in one sentence of business language, not Django language.
2. Choices don't constrain the database. Write the `CheckConstraint` that would make `status` reject `"banana"`. Would you add it? What does it cost when you add a new status later?
3. Why does `ordering = ["project"]` add a JOIN while `["project_id"]` doesn't?
4. `close()` doesn't call `save()`. Give one concrete reason that's the better design.

## Read the source (optional)

`django/db/models/deletion.py`: `Collector.collect` and the `CASCADE`/`PROTECT`/`SET_NULL` functions at the top. They're tiny. Seeing that `on_delete` is a callable Django invokes makes "Python-side, not SQL-side" obvious.
