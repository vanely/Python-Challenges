# R1.05 — Filtering, search, ordering, pagination

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/r1/test_r1_05_filtering.py`

## What you'll have at the end

```
GET .../issues/?status=open&status=in_progress
GET .../issues/?assignee=bob&label=bug&min_priority=3
GET .../issues/?search=login
GET .../issues/?ordering=-priority
```

Invalid filter values are rejected with 400. Ordering is restricted to an allow-list. Results are paginated.

## Concepts

### Filter backends

`GenericAPIView.filter_queryset(qs)` passes the queryset through each class in `filter_backends`, in order. Each backend reads query parameters and returns a narrowed queryset. `list()` calls it, and so does `get_object()`. So filters apply to detail lookups too, which is usually harmless and occasionally surprising.

- **`DjangoFilterBackend`** (django-filter) uses a **`FilterSet`**: a declarative class, effectively a *form* for query parameters. It validates values (a 400 for `?status=nonsense`) and maps them to ORM lookups.
- **`SearchFilter`** handles `?search=` against `search_fields`, case-insensitive `icontains`, ORed across fields and ANDed across words. It's fine for thousands of rows. For real full-text search use PostgreSQL's `SearchVector` (`django.contrib.postgres.search`) or a search engine.
- **`OrderingFilter`** handles `?ordering=a,-b` against `ordering_fields`.

### The ordering allow-list is a security control

If clients could order by any field, including across relations, then `?ordering=reporter__password` sorts issues by their reporters' password hashes. By running many such requests with crafted data, an attacker can learn information about values they can't read. Ordering is a side channel. Always set `ordering_fields` to an explicit list. Fields not on the list are **ignored** (not rejected), and the checkpoint tests that.

Filters across relations carry the same risk. A FilterSet only exposes what you declare. Never use `fields = "__all__"` on a FilterSet, for the same reason as on serializers.

### M2M filters and duplicates

`?label=bug` filters `labels__name="bug"`, which joins `tracker_issue_labels` and `tracker_label`. Could an issue appear twice? Only if it had two labels that *both* matched. For an exact name that's impossible, since names are unique per project (D2.02's constraint). For lookups that could match several related rows (`labels__name__startswith="b"`), you'd need `distinct=True` on the filter. Knowing *why* a join can or can't duplicate is the D2 skill again.

### Choosing a pagination style

| Style | Query | Strengths | Weaknesses |
|---|---|---|---|
| `PageNumberPagination` (`?page=3`) | `COUNT(*)` + `LIMIT 20 OFFSET 40` | simple, has total count, jump to page N | `OFFSET` scans and discards rows, so page 5,000 is slow. Inserts between requests shift pages (items skipped or repeated) |
| `LimitOffsetPagination` (`?limit=20&offset=40`) | same | client chooses size | same |
| `CursorPagination` (`?cursor=...`) | `WHERE (ordering key) < last_seen LIMIT 20`, no COUNT | constant cost at any depth, stable under inserts, perfect for feeds and infinite scroll | no total count, no jumping to page N, needs a unique and immutable ordering |

trackr keeps page numbers (people want "3 of 7"). A busy activity feed would use cursors. You can set `pagination_class` per view.

## Build

### 1. Settings and app

```python
INSTALLED_APPS = [..., "django_filters", ...]

REST_FRAMEWORK = {
    ...,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}
```

### 2. `api/filters.py`

```python
import django_filters

from tracker.models import Issue


class IssueFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=Issue.Status.choices)
    assignee = django_filters.CharFilter(field_name="assignee__username")

    class Meta:
        model = Issue
        fields = ["status", "assignee"]
```

`MultipleChoiceFilter` accepts repeated parameters (`?status=open&status=in_progress`), validates each against the choices, and ORs them.

### 3. Wire into the ViewSet

```python
from .filters import IssueFilter

class IssueViewSet(viewsets.ModelViewSet):
    ...
    filterset_class = IssueFilter
    search_fields = ["title", "body"]
    ordering_fields = ["number", "priority", "created_at", "updated_at"]
```

Add `search_fields = ["name", "description"]` and `ordering_fields = ["name", "created_at"]` to `ProjectViewSet` as well.

The ordering filter applies *after* `get_queryset()`'s `.order_by("-number")` and replaces it when `?ordering=` is given.

### 4. Your turn: two more filters

- `label`: issues having a label with exactly this name;
- `min_priority`: issues with `priority >= value`. A non-numeric value must give a 400.

<details><summary>Hint</summary>

Both are a `field_name` plus, for one of them, a `lookup_expr`. Look at `NumberFilter` in the django-filter docs.
</details>

### 5. Try the browsable API

The list page now has a "Filters" button. django-filter renders the FilterSet as an HTML form, since it *is* a form underneath.

## Checkpoint

```bash
uv run pytest ../checkpoints/r1/test_r1_05_filtering.py
uv run pytest ../checkpoints/d1 ../checkpoints/d2 ../checkpoints/r1   # all green (R2's checkpoints fail until you do R2)
```

## Pitfalls

- **Missing `ordering_fields`.** DRF then allows any field the serializer can read. That's narrower than "any field", but still not something you chose on purpose. Be explicit.
- **`?search=` over large text columns in production.** `icontains` is a full table scan.
- **Filtering in `get_queryset()` from `request.query_params` by hand.** You lose validation (`int("abc")` gives a 500) and schema documentation (R2.02).
- **Deep pagination with page numbers on huge tables.** Watch for `OFFSET` in slow-query logs.

## Explain it back

1. How can ordering by an unreadable field leak information? Describe the attack in steps.
2. Why can't `?label=bug` return duplicates here, and which change to the domain would make it possible?
3. You're building an infinite-scroll activity feed with 10 million rows. Which pagination class do you choose, which ordering, and why?
4. R1 retrospective: compare this API with the FastAPI service from Stage 1. What did DRF give you for free, and what was harder to see?
