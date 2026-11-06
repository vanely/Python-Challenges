# D2.03 — Aggregation: annotate, aggregate, fan-out, and subqueries

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/d2/test_d2_03_aggregation.py`

## What you'll have at the end

A `/dashboard/` page listing your projects. For each one it shows:
- open and closed issue counts;
- member count;
- the time of the most recent comment.

All of it is computed in **one** SQL query, and the numbers are correct. The second part is harder than it sounds.

## Concepts

### `aggregate` vs `annotate`

- **`aggregate()`** collapses a whole QuerySet into **one dict**. It's terminal and runs immediately.

  ```python
  Issue.objects.filter(project=p).aggregate(total=Count("id"), top=Max("priority"))
  # {'total': 12, 'top': 4}
  ```

- **`annotate()`** adds a computed column **to each row**. The QuerySet stays a QuerySet: chainable and lazy.

  ```python
  Project.objects.annotate(issue_count=Count("issues"))
  # each Project now has .issue_count
  ```

  Under the hood, `annotate` with an aggregate function over a relation is a `LEFT JOIN` plus `GROUP BY` on the model's columns.

### Conditional aggregation

```python
Count("issues", filter=Q(issues__status="closed"))
```

This compiles to `COUNT(...) FILTER (WHERE ...)` on PostgreSQL and SQLite, or to an equivalent `CASE WHEN` elsewhere. It counts a subset without a second query or a second JOIN. Two counts over the same relation share one JOIN.

### The fan-out bug (you will hit this)

Counting **two different many-valued relations** in one query gives wrong answers:

```python
Project.objects.annotate(issues_n=Count("issues"), members_n=Count("memberships"))
```

Picture the SQL: `project LEFT JOIN issue LEFT JOIN membership`. A project with 4 issues and 3 members produces **4 × 3 = 12 rows**, and both counts report 12. This was measured on this exact schema:

```
naive:    issues_n=12, members_n=12        (truth: 4 and 3)
distinct: issues_n=4,  members_n=3
```

Fixes:
- **`Count(..., distinct=True)`** counts distinct primary keys, so duplicates from the other join collapse. It's correct for `Count`, but **useless for `Sum`/`Avg`**: `Sum("issues__priority", distinct=True)` sums distinct *values*, which is a different and wrong answer.
- **Subqueries** compute each aggregate separately, with no shared join. They're always correct, and the right tool for `Sum`/`Avg` across fan-out.

### Filter, then annotate: the join gets reused

Order matters with multi-valued relations:

```python
Project.objects.filter(memberships__user=me).annotate(members_n=Count("memberships"))
```

The `filter()` joined `memberships` and restricted it to *your* membership row. The `annotate()` **reuses that same join**, so it counts only the rows the filter left: always 1. On a project with 3 members, measured:

```
filter → annotate:     members_n = 1
annotate → filter:     members_n = 3
```

The Django docs describe this in "Order of annotate() and filter() clauses". It's correct SQL semantics, and a surprise if you think of `filter` and `annotate` as independent.

The robust way to say "my projects" when you also aggregate over memberships is a **subquery that doesn't share the join**:

```python
my_ids = request.user.memberships.values("project_id")   # a QuerySet, not evaluated
Project.objects.filter(pk__in=my_ids).annotate(members_n=Count("memberships", distinct=True))
```

`pk__in=<QuerySet>` compiles to `WHERE id IN (SELECT project_id FROM tracker_membership WHERE user_id = ...)`. That's one query, and the outer join is free to count all memberships.

### Subquery and OuterRef

"The latest comment time per project" is neither a count nor a sum. It's *a value from one related row*. `Max("issues__comments__created_at")` works here, but the general tool is a correlated subquery:

```python
from django.db.models import OuterRef, Subquery

latest = (
    Comment.objects.filter(issue__project=OuterRef("pk"))
    .order_by("-created_at")
    .values("created_at")[:1]
)
Project.objects.annotate(last_comment_at=Subquery(latest))
```

- `OuterRef("pk")` refers to the outer query's row, the project being annotated.
- `.values("created_at")[:1]` makes the subquery return one column and one row, which is required for `Subquery` as a value.
- Use this pattern when you need *a different column of the latest row* (its author or body), which `Max` can't give you.

### `F` expressions

`F("field")` refers to a column inside the database, so comparisons and updates happen in SQL:

```python
Issue.objects.filter(updated_at__gt=F("created_at"))           # edited issues
Project.objects.filter(pk=p.pk).update(next_issue_number=F("next_issue_number") + 1)  # atomic increment
```

The second line is the seed of D2.04.

## Build

### 1. The dashboard view

In `tracker/views.py` (add `Count`, `Q`, `OuterRef` and `Subquery` to your `django.db.models` import, and import `Comment`):

```python
@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    my_project_ids = request.user.memberships.values("project_id")
    projects = (
        Project.objects.filter(pk__in=my_project_ids)
        .annotate(
            open_count=Count("issues", filter=~Q(issues__status="closed"), distinct=True),
            closed_count=Count("issues", filter=Q(issues__status="closed"), distinct=True),
            member_count=Count("memberships", distinct=True),
        )
        .order_by("name")
    )
    return render(request, "tracker/dashboard.html", {"projects": projects})
```

URL: `path("dashboard/", views.dashboard, name="dashboard")`, plus a nav link in `base.html`.

Template `tracker/templates/tracker/dashboard.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
  <h1>Dashboard</h1>
  <table>
    <thead><tr><th>Project</th><th>Open</th><th>Closed</th><th>Members</th><th>Last comment</th></tr></thead>
    <tbody>
      {% for p in projects %}
        <tr>
          <td><a href="{{ p.get_absolute_url }}">{{ p.name }}</a></td>
          <td>{{ p.open_count }}</td>
          <td>{{ p.closed_count }}</td>
          <td>{{ p.member_count }}</td>
          <td>{{ p.last_comment_at|default:"—" }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
```

### 2. Break it on purpose first

Before trusting the version above, reproduce both bugs and record what you see in `NOTES.md`:
1. Remove every `distinct=True`. Create a project with 3 members, 4 issues and some comments. What does the dashboard show?
2. Put `distinct=True` back, but change the first line to `Project.objects.filter(memberships__user=request.user)`. What's the member count now?
3. Print `projects.query` for each variant and find the `JOIN`s and the `GROUP BY`.

### 3. Your turn: last comment time

Add `last_comment_at` to the annotation using `Subquery`/`OuterRef` (not `Max`). The page must stay at a constant number of queries however many projects you have. The checkpoint allows at most 4, counting session and user lookups.

<details><summary>Hint</summary>

The subquery starts from `Comment` and filters on the path from a comment to its issue's project, compared with `OuterRef("pk")`. Order newest first, keep one column, and slice to one row.
</details>

### 4. Your own test

In `tests/test_dashboard.py`, write a test that would have caught bug 1 from step 2: a project with several members *and* several issues, asserting exact counts. A test with one member or one issue wouldn't catch it. Write in a comment why.

## Checkpoint

```bash
uv run pytest ../checkpoints/d2/test_d2_03_aggregation.py
```

## Pitfalls

- **Two `Count`s over different multi-valued relations without `distinct=True`**: fan-out.
- **`Sum`/`Avg` across a fan-out join**: `distinct` doesn't save you; use subqueries.
- **`filter()` on a relation before `annotate()` over the same relation**: the count is restricted by the filter.
- **Default `Meta.ordering` and aggregation.** Since Django 3.1, `Meta.ordering` is ignored in `GROUP BY` queries. Older code that relied on it was silently grouping by extra columns. If you need order, call `.order_by()` explicitly, as the view does.
- **Counting in Python** (`len(project.issues.all())` in a loop). That's what this step replaces.

## Explain it back

1. Explain the fan-out bug with a drawing of the joined rows for a project with 2 issues and 3 members.
2. Why does `distinct=True` fix `Count` but not `Sum`?
3. Why does `filter(memberships__user=me)` change `Count("memberships")`, but `filter(pk__in=my_ids)` doesn't?
4. When would you choose `Subquery` over `Max` for "latest comment"?

## Read the docs

"Aggregation" in the Django topic guide, in full. Especially "Order of annotate() and filter() clauses" and "Combining multiple aggregations", which is the fan-out bug in Django's own words.
