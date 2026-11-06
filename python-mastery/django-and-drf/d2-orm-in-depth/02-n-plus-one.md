# D2.02 — Labels, and making page cost independent of row count

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/d2/test_d2_02_n_plus_one.py`

## What you'll have at the end

- A `Label` model (per-project tags like `bug` and `ui`) attached to issues many-to-many.
- A project page that runs **the same number of queries for 2 issues as for 2,000**.

## Concepts

### N+1, precisely

```python
issues = project.issues.all()                # 1 query
for issue in issues:
    issue.assignee.username                  # +1 query per issue (FK not loaded)
    [l.name for l in issue.labels.all()]     # +1 query per issue (M2M not loaded)
```

With 50 issues that's 1 + 50 + 50 = 101 queries. Each is fast on its own, so nothing looks wrong in development with 5 rows. In production, with 500 rows and a database 2 ms away over the network, the page takes a second. **The fix is never "make the query faster". It's "make fewer queries."**

### `select_related`: JOIN, for single-valued relations

```python
project.issues.select_related("assignee", "reporter")
```

This adds `LEFT OUTER JOIN accounts_user ...` (an `INNER JOIN` for non-nullable FKs) and builds the related objects from the same rows. It works for **forward ForeignKey and OneToOne** relations, the ones where each row has *at most one* related object, so joining doesn't multiply rows. You can follow chains: `select_related("project__owner")`.

### `prefetch_related`: second query, joined in Python

```python
project.issues.prefetch_related("labels")
```

This runs the issue query, then **one more** query, roughly:

```sql
SELECT ... FROM tracker_label
INNER JOIN tracker_issue_labels ON ...
WHERE tracker_issue_labels.issue_id IN (1, 2, 3, ...)
```

Django then attaches each issue's labels in Python. It works for **many-valued** relations (M2M, reverse FK), where a JOIN would duplicate the parent rows. The cost is 1 extra query per prefetched relation, *not* per row.

The two combine:

```python
project.issues.select_related("assignee").prefetch_related("labels")   # 2 queries total
```

### `Prefetch` objects: filtering and shaping the prefetch

```python
from django.db.models import Prefetch

Project.objects.prefetch_related(
    Prefetch("issues", queryset=Issue.objects.open().select_related("assignee"), to_attr="open_issues")
)
```

- `queryset=` customises the second query. You can filter it, and even `select_related` *within* it.
- `to_attr=` stores the result as a plain **list** attribute (`project.open_issues`) instead of populating `project.issues.all()`. Use it whenever you filter, so nobody mistakes a filtered cache for the full relation.

### What uses the prefetch cache and what doesn't

After `prefetch_related("labels")`:
- `issue.labels.all()` uses the cache;
- `issue.labels.count()` uses the cache;
- `issue.labels.filter(name="bug")` runs a **new query**. It's a new QuerySet, and the cache can't answer arbitrary filters;
- `issue.labels.order_by("name")` runs a **new query** too.

So filter in Python over `.all()` (`[l for l in issue.labels.all() if l.name == "bug"]`), or move the filter into a `Prefetch(queryset=...)`.

### Known related objects (why some loops don't N+1)

Iterating `project.issues.all()` and touching `issue.project` costs nothing. Django sets each issue's `project` to the object you came from. `Issue.objects.filter(project=project)` doesn't get this. Prove it yourself in the experiments below.

### Measuring instead of guessing

- In tests: `django_assert_num_queries(n)` / `django_assert_max_num_queries(n)`, or `CaptureQueriesContext(connection)` to count and inspect.
- The checkpoint for this step uses the most robust test there is: **render the page with 2 issues and with 20; the counts must be equal.** It doesn't care what the number is, only that it doesn't grow.
- In development: SQL logging, or `django-debug-toolbar` (worth installing on any real project).

## Build

### 1. The model

In `tracker/models.py`, after `Membership`:

```python
class Label(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#888888")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="unique_label_per_project"),
        ]

    def __str__(self) -> str:
        return self.name
```

And on `Issue`:

```python
    labels = models.ManyToManyField(Label, blank=True, related_name="issues")
```

`blank=True` because issues don't need labels. M2M fields never use `null=True`; it has no meaning there, because the relation lives in a separate table.

```bash
uv run python manage.py makemigrations tracker
uv run python manage.py migrate
```

Register `Label` in the admin with `list_display = ["name", "project", "color"]` and a project filter. Make a few labels in a project and attach them to issues.

### 2. Forms

Add `"labels"` to `IssueForm.Meta.fields`, render it as checkboxes, and **restrict its queryset** just like `assignee`. A label from another project must be rejected:

```python
class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["title", "body", "priority", "assignee", "labels"]
        widgets = {"labels": forms.CheckboxSelectMultiple}

    def __init__(self, *args: Any, project: Project, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = project.members.all()
        self.fields["labels"].queryset = project.labels.all()
```

Now the D1.05 trap goes off: `issue_create` uses `form.save(commit=False)`, which can't save M2M data before the issue exists. Add the call:

```python
            issue.save()
            form.save_m2m()
            return redirect(issue)
```

Create an issue with labels in the browser and confirm they stuck. Then remove `form.save_m2m()`, try again, and watch them silently vanish. Put it back. D2.04 replaces this whole block.

`IssueUpdateView` needs nothing. `UpdateView` calls `form.save()` with `commit=True`, which saves M2M data itself.

### 3. Render labels on the project page

Add a "Labels" column to `project_detail.html`:

```html
<td>{% for label in issue.labels.all %}{{ label.name }} {% endfor %}</td>
```

Turn on SQL logging, load a project with ten labelled issues, and count the queries. You should see N+1.

### 4. Your turn: fix it, and prove it

1. Make the project page's query count independent of the number of issues. The page shows each issue's assignee *and* labels. Check the logs: you should see exactly one query for issues and one for labels.
2. Add a `with_related()` method to `IssueQuerySet` that loads everything an issue page needs (project, reporter, assignee, labels). Use it in `issue_detail`.
3. Write your own test in `tests/test_queries.py` that renders the project page with 3 issues and with 30 and asserts equal query counts. Use the shape of the checkpoint test, but write it yourself.

<details><summary>Hint</summary>

Which of the two tools handles single-valued relations, and which handles many-valued ones? You need both, chained.
</details>

### 5. Experiments (results go in `NOTES.md`)

In the shell, with logging on:

```python
p = Project.objects.first()
[i.project.name for i in p.issues.all()]                     # how many queries?
[i.project.name for i in Issue.objects.filter(project=p)]    # and now?

qs = p.issues.prefetch_related("labels")
[i.labels.count() for i in qs]                               # queries?
[i.labels.filter(name="bug").exists() for i in qs]           # queries?
```

## Checkpoint

```bash
uv run pytest ../checkpoints/d2/test_d2_02_n_plus_one.py
uv run pytest ../checkpoints/d1 ../checkpoints/d2/test_d2_01_querysets.py
```

## Pitfalls

- **`select_related` on an M2M**: Django raises `FieldError` ("Invalid field name(s) given in select_related"). Use `prefetch_related`.
- **Prefetching, then calling `.filter()` on the relation**: the prefetch is wasted *and* you're back to N+1.
- **Prefetching everything "just in case".** Each prefetch is a real query with an `IN (...)` list. Prefetch what the page renders.
- **Fixing N+1 in the view but rendering a property in the template that queries anyway**, like a model method calling `self.comments.count()`. Look for queries in the log, not in your view code.

## Explain it back

1. Why can't `select_related` follow a many-to-many relation? Answer in terms of what happens to the result rows.
2. With `select_related("assignee").prefetch_related("labels")` and 40 issues, exactly how many queries run, and what does each one do?
3. Explain the two experiment results about `i.project.name`.
4. Why does the checkpoint compare two counts instead of asserting a fixed number?
