# D1.03 — The admin as an internal tool

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/d1/test_d1_03_admin.py`

## What you'll have at the end

An admin where a support person can:
- find any issue by text;
- filter by status, priority and project;
- see the assignee without opening the record;
- manage project memberships on the project page.

## Concepts

### What the admin is, and isn't

`django.contrib.admin` generates CRUD pages from your models by introspecting `_meta`: fields, relations, choices, `blank`/`null`. It's one of Django's biggest productivity wins, and it's meant for **trusted staff**, not end users. Its permission model is per-model (`add`/`change`/`delete`/`view`), not per-row. Every user with `is_staff=True` and the right permissions sees *every* row. So the admin never replaces the user-facing views you build in D1.04. It's the back office.

### `ModelAdmin` is configuration

`admin.site.register(Issue)` gives you a usable page. A `ModelAdmin` subclass tunes it, and nearly every option is a declarative class attribute:

| Option | Effect | Cost to watch |
|---|---|---|
| `list_display` | columns on the changelist | each FK column is a query per row… |
| `list_select_related` | …unless you list it here: one JOIN instead of N queries | |
| `list_filter` | sidebar filters (choices, FKs, dates, booleans) | FK filters load every related row for the sidebar |
| `search_fields` | the search box: `icontains` across the listed fields, ORed | `icontains` can't use a normal index; fine for thousands of rows, slow for millions |
| `autocomplete_fields` | AJAX select instead of a `<select>` with every user | the target admin **must** define `search_fields` |
| `readonly_fields` | shown, not editable | |
| `prepopulated_fields` | fills `slug` from `name` with JavaScript as you type | |
| `inlines` | edit related rows on the parent's page | |

### The N+1 query problem, first sighting

With `list_display = ["__str__", "project", "assignee"]` and 100 issues, rendering each row touches `issue.project` and `issue.assignee`. Each access is a separate query unless the queryset already fetched them. That's 1 query for the list plus 2 × 100 for the related objects. **N+1.** `list_select_related = ["project", "assignee"]` tells the admin to JOIN them in the original query. D2.02 covers this properly; the admin is where most people first see it.

## Build

### 1. `tracker/admin.py`

```python
from django.contrib import admin

from .models import Comment, Issue, Membership, Project


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["__str__", "project", "status", "priority", "assignee", "created_at"]
    list_filter = ["status", "priority", "project"]
    search_fields = ["title", "body"]
    list_select_related = ["project", "assignee"]
    autocomplete_fields = ["reporter", "assignee"]
    readonly_fields = ["number", "created_at", "updated_at"]


admin.site.register(Comment)
```

`autocomplete_fields = ["reporter", "assignee"]` needs the *User* admin to define `search_fields`. Django's `UserAdmin` already does (username, names, email). That's why you registered it in D1.01 instead of a bare `ModelAdmin`.

Why is `number` read-only? Issue numbers are identifiers that people paste into chat and commit messages. Renumbering breaks every reference. In D1.05 the number is assigned by code, and in D2.04 by a service with a lock. Nobody types it in.

### 2. Your turn: `ProjectAdmin`

Register `Project` with an admin that:
- shows name, slug, owner and created date in the list;
- searches by name and slug;
- fills `slug` from `name` as you type;
- edits **memberships inline** on the project page as a compact table. New users can be picked with autocomplete, and no blank extra rows are shown by default.

<details><summary>Hint 1</summary>

Inlines are classes too: `admin.TabularInline` or `admin.StackedInline`, with `model = ...`. Look up the inline's `extra` option.
</details>

<details><summary>Hint 2</summary>

`autocomplete_fields` works on inlines as well. Which model's field are you autocompleting?
</details>

### 3. Use it

```bash
uv run python manage.py runserver
```

As your superuser:
1. create two more users;
2. create a project, adding all three as members inline (one admin, two members);
3. create five issues, assigning some. **Not in the admin:** `number` is read-only there and nothing assigns it until D2.04, so the add form fails with `IntegrityError: NOT NULL constraint failed: tracker_issue.number`. (Try it once and read the error, then go back.) Create them in `uv run python manage.py shell`, passing `number=1`, `number=2`, … explicitly. Edit them in the admin afterwards.

Then:
- search for a word in an issue body;
- filter by status;
- try to delete a user who reported an issue and read the error page. That's `PROTECT` from D1.02, rendered by the admin.

### 4. See the queries (optional but recommended)

Add this to the bottom of `config/settings.py` temporarily, then reload the issue changelist and watch the terminal:

```python
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django.db.backends": {"handlers": ["console"], "level": "DEBUG"}},
}
```

Comment out `list_select_related` and reload. Count the queries. Put it back. (`django.db.backends` only logs while `DEBUG = True`.) Remove the logging block when you're done; R2.03 adds a permanent, configurable one.

## Checkpoint

```bash
uv run pytest ../checkpoints/d1/test_d1_03_admin.py
```

## Pitfalls

- **`autocomplete_fields` pointing at a model whose admin has no `search_fields`.** System check `admin.E040` stops the server, which is good: the error tells you exactly what to add.
- **Giving end users `is_staff`** so they can "just use the admin". The admin has no row-level scoping. A member of project A would see project B.
- **Callable `list_display` columns that query**, e.g. `def open_count(self, obj): return obj.issues.open().count()`. That's N+1 again. Annotate in `get_queryset` instead (you'll learn `annotate` in D2.03).

## Explain it back

1. Why is the admin unsuitable as your end-user interface, even with Django's permission system?
2. Describe the N+1 problem in your own words, with numbers, for a changelist of 100 issues showing `project` and `assignee`.
3. What does `admin.site.register(Model, ModelAdminClass)` actually store, and where? (Hint: the checkpoint test reads it.)
