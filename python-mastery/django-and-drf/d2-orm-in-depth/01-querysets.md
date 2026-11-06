# D2.01 — QuerySets: lazy, cached, chainable

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/d2/test_d2_01_querysets.py`

## What you'll have at the end

- An `IssueQuerySet` with chainable domain methods (`open()`, `visible_to(user)`), installed as `Issue.objects`.
- Your first tests of your own, using pytest-django and factory_boy.

## Concepts

### A QuerySet is a query *description*

```python
qs = Issue.objects.filter(project=p).exclude(status="closed").order_by("-priority")
```

No SQL has run. `filter`, `exclude`, `order_by`, `select_related` and `annotate` each **return a new QuerySet** wrapping a modified `Query` object. The original is untouched, so you can branch from a shared base:

```python
base = Issue.objects.filter(project=p)
urgent = base.filter(priority=4)        # base is unchanged
recent = base.order_by("-created_at")
```

`print(qs.query)` shows the SQL that *would* run. It's approximate: parameters are interpolated for display only.

### When does SQL actually run?

A QuerySet **evaluates** (hits the database) when you need its rows:

| Trigger | Notes |
|---|---|
| iteration: `for i in qs`, `list(qs)` | the common case |
| `len(qs)` | fetches **all rows**, then counts in Python. Use `qs.count()` if you only need the number |
| `bool(qs)`, `if qs:` | fetches all rows. Use `qs.exists()` |
| `repr(qs)` | in the shell; limited to 21 rows |
| slicing with a step, `qs[::2]` | |
| pickling / caching | |

Methods that *return* something other than a QuerySet run their own query immediately: `.get()`, `.first()`, `.count()`, `.exists()`, `.aggregate()`, `.update()`, `.delete()`. Plain slicing `qs[:10]` doesn't evaluate. It adds `LIMIT 10` and returns a QuerySet.

### The result cache

The first evaluation stores the rows in `qs._result_cache`. Iterating the **same QuerySet object** again uses the cache, with no new query. But:

```python
for i in project.issues.all(): ...   # query
for i in project.issues.all(): ...   # another query: .all() returned a NEW QuerySet
```

and:

```python
qs = Issue.objects.all()
qs[0]    # query with LIMIT 1, not cached
qs[0]    # query again
list(qs) # full query, now cached
qs[0]    # from cache
```

The rule: **hold on to a QuerySet if you'll use it twice.** In templates, `{% with issues=project.issues.all %}` does that.

### Managers vs QuerySets

`Issue.objects` is a **Manager**: the entry point that creates QuerySets. You want domain vocabulary such as `Issue.objects.visible_to(user).open()`, and it has to work *in any order and after `filter()`*:

```python
Issue.objects.filter(project=p).open()   # needs open() on the QuerySet, not the Manager
```

So define the methods on a **QuerySet subclass** and build the manager from it:

```python
class IssueQuerySet(models.QuerySet["Issue"]):
    def open(self) -> "IssueQuerySet":
        return self.exclude(status=Issue.Status.CLOSED)

class Issue(models.Model):
    ...                                   # fields
    objects = IssueQuerySet.as_manager()

    class Meta: ...
```

`as_manager()` creates a Manager class that proxies your QuerySet methods. Every method returns `self.filter(...)` and friends, so it returns a new QuerySet and chains.

What belongs here: **reusable, composable filters with a domain name**. "Open", "visible to this user", "overdue". Business *actions* that write data belong elsewhere (D2.04).

### Testing with pytest-django

The checkpoints have been using it all along. The essentials:
- `@pytest.mark.django_db` (or a module-level `pytestmark`) allows database access. Each test runs **inside a transaction that's rolled back** at the end, which is fast and isolates tests.
- **Fixtures:** `client` (a Django test client), `django_user_model`, `django_assert_num_queries(n)`, `django_assert_max_num_queries(n)`, `settings` (override per test).
- The test database is created fresh for the run (SQLite: in memory) by applying your migrations. **So tests also check that your migrations work.**

**factory_boy** builds valid objects with sensible defaults, so each test states only what it cares about:

```python
issue = IssueFactory(status="closed")     # project, reporter, number… filled in
```

## Build

### 1. The QuerySet

In `tracker/models.py`, above `Issue`:

```python
class IssueQuerySet(models.QuerySet["Issue"]):
    def open(self) -> IssueQuerySet:
        return self.exclude(status=Issue.Status.CLOSED)
```

and inside `Issue`, after the fields and before `class Meta`. That's Django's conventional order, and ruff's `DJ012` rule enforces it:

```python
    objects = IssueQuerySet.as_manager()
```

- `from __future__ import annotations` (already at the top from D1.02) makes the return annotation `IssueQuerySet` legal before the class body finishes.
- `models.QuerySet["Issue"]` works at runtime because Django defines `__class_getitem__` on `QuerySet`. It's for type checkers only.
- Using `Issue.Status` inside the method is fine even though `Issue` is defined later in the file: the method body only runs when called, and by then the name exists.

No migration is needed. Managers aren't schema.

### 2. Your turn: `visible_to(user)`

Add `visible_to(user)`, which returns the issues in projects the user is a member of. Then use it in `issue_detail` and `IssueUpdateView`, replacing whatever scoping you wrote in D1.

Requirements:
- chainable in any order with `open()` and `filter()`;
- **no duplicate rows**. Think about whether your join can produce more than one row per issue.

<details><summary>Hint</summary>

The relation path from `Issue` to the membership's user is `project__memberships__user`. Can a project have two memberships for the same user? Which constraint from D1.02 answers that?
</details>

### 3. Your own tests

Create `trackr/tests/__init__.py` (empty) and `trackr/tests/factories.py`:

```python
import factory
from django.contrib.auth import get_user_model

from tracker.models import Issue, Membership, Project


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.django.Password("pw")


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Project {n}")
    slug = factory.Sequence(lambda n: f"project-{n}")
    owner = factory.SubFactory(UserFactory)

    @factory.post_generation
    def owner_is_admin(self, create: bool, extracted: object, **kwargs: object) -> None:
        if create:
            Membership.objects.create(project=self, user=self.owner, role=Membership.Role.ADMIN)


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue

    project = factory.SubFactory(ProjectFactory)
    number = factory.Sequence(lambda n: n + 1)
    title = factory.Faker("sentence", nb_words=4)
    reporter = factory.SelfAttribute("project.owner")
```

- `Sequence` gives unique values across a test run.
- `SubFactory` builds a related object on demand.
- `SelfAttribute("project.owner")` reuses the issue's own project's owner instead of creating yet another user.
- `post_generation` runs after the object is saved. `skip_postgeneration_save = True` stops factory_boy from saving the project a second time afterwards: the hook creates a *different* row, so the project itself hasn't changed. Without it you get a `DeprecationWarning` from factory_boy 3.3.
- `factory.Faker` needs the `Faker` package, which factory_boy depends on.

`trackr/tests/test_querysets.py`. Write at least three tests of your own:
- `open()` excludes closed issues and keeps `in_progress` ones;
- `visible_to()` excludes other people's projects;
- the two chain in both orders.

Then **one test that proves laziness**:

```python
def test_filters_do_not_hit_the_database(django_assert_num_queries):
    user = UserFactory()
    with django_assert_num_queries(0):
        qs = Issue.objects.open().visible_to(user).order_by("-priority")
    assert "ORDER BY" in str(qs.query)
```

Then an experiment. `UserFactory.build()` creates an *unsaved* user. **Predict** what `Issue.objects.visible_to(UserFactory.build())` does: a query? an empty result? an error? Run it in the shell, then explain what happened and why that's the right design in `NOTES.md`.

Run your tests:

```bash
uv run pytest tests/
```

### 4. Experiments in the shell

With SQL logging on (see the D2 README), in `uv run python manage.py shell`:

```python
qs = Issue.objects.open()
print(qs.query)
len(qs); len(qs)                  # how many queries?
qs.count(); qs.count()            # and now?
bool(Issue.objects.all()); Issue.objects.exists()   # compare the SQL
Issue.objects.all()[:3]           # look for LIMIT
```

## Checkpoint

```bash
uv run pytest ../checkpoints/d2/test_d2_01_querysets.py
uv run pytest ../checkpoints/d1          # still green?
```

## Pitfalls

- **Methods on a custom `Manager` instead of the QuerySet.** They work on `Issue.objects` and break after `.filter()`.
- **`if qs:` / `len(qs)` when you need existence or a count.** That fetches every row.
- **Evaluating inside a loop**: `for p in projects: p.issues.count()`. That's one query per project. D2.03 fixes it with `annotate`.
- **Assuming `.all()` is free and cached.** It's a new QuerySet each time.

## Explain it back

1. Name four operations that evaluate a QuerySet and two that only modify it.
2. Why must `open()` live on a QuerySet subclass rather than a Manager subclass?
3. Explain the result of the unsaved-user experiment. What bug would silently happen if Django allowed it?
4. What does wrapping every test in a rolled-back transaction buy you, and what can it *not* test? (Hint: D2.04 needs `transaction=True`.)

## Read the source (optional)

`django/db/models/query.py`: `QuerySet._fetch_all`, `__iter__`, `__len__`, `__bool__`, `_chain`, `_clone`. Then `django/db/models/manager.py`: `BaseManager.from_queryset` and `_get_queryset_methods`, which show how `as_manager()` copies your methods.
