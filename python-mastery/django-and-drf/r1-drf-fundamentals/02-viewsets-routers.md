# R1.02 — Generic views, ViewSets, routers, pagination

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/r1/test_r1_02_viewsets.py`

## What you'll have at the end

Full CRUD for projects at `/api/projects/` and `/api/projects/{slug}/`. It comes from one `ModelViewSet` class with a scoped `get_queryset()` and a router that generates the URLs. List responses are paginated.

## Concepts

### `GenericAPIView`: the same hooks as D1.06

DRF's generic views mirror Django's generic CBVs, with the same "override one hook" philosophy:

| Hook | Default | You override it to… |
|---|---|---|
| `get_queryset()` | `self.queryset.all()` | **scope data to the user** (always), add `select_related` |
| `get_object()` | `get_queryset()` → `filter_queryset()` → lookup by `lookup_field` → **`check_object_permissions()`** | rarely; change `lookup_field` instead |
| `get_serializer_class()` | `self.serializer_class` | use different serializers for read and write |
| `get_serializer_context()` | `{"request", "format", "view"}` | add things like the current project (R1.04) |
| `filter_queryset(qs)` | runs `filter_backends` | (R1.05) |
| `paginate_queryset(qs)` | uses `pagination_class` | |
| `perform_create(serializer)` / `perform_update` / `perform_destroy` | `serializer.save()` / `instance.delete()` | inject server values: `serializer.save(owner=...)` |

Then **mixins** supply the handlers: `ListModelMixin.list`, `CreateModelMixin.create`, `RetrieveModelMixin.retrieve`, `UpdateModelMixin.update`/`partial_update`, `DestroyModelMixin.destroy`. Each is ~10 lines calling the hooks above. Read them on [cdrf.co](https://www.cdrf.co/). They're short, and reading them is how DRF stops being magic.

### ViewSets and routers

A **ViewSet** groups the handlers for one resource into one class, using *action* names (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`) instead of HTTP methods. `ModelViewSet` is all six mixins plus `GenericViewSet`.

A **Router** turns a ViewSet into URL patterns:

```python
router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
```

| URL | Method → action | URL name |
|---|---|---|
| `projects/` | GET → `list`, POST → `create` | `project-list` |
| `projects/{lookup}/` | GET → `retrieve`, PUT → `update`, PATCH → `partial_update`, DELETE → `destroy` | `project-detail` |

- `DefaultRouter` also adds an API root view at `/api/` and format suffixes.
- **Pass `basename` explicitly.** DRF can infer it only from a class-level `queryset` attribute, and you won't have one: your queryset depends on the user, so it's built in `get_queryset()`.

### Why there's no class-level `queryset`

```python
class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()        # ← don't
```

Every handler, including `retrieve`, `update` and `destroy` via `get_object()`, starts from `get_queryset()`. Override it to scope by membership and the whole ViewSet is scoped: non-members get 404 on detail, update and delete, for free. A class-level `queryset` invites someone to forget the override. This is the D1.04 rule ("scope the query, don't fetch then check") in DRF form.

### Pagination

An unpaginated list endpoint is a time bomb: it's fine with 20 rows and an outage with 200,000. Turn pagination on globally:

```python
REST_FRAMEWORK = {
    ...,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
```

Responses become `{"count": N, "next": url|null, "previous": url|null, "results": [...]}`. `count` costs a `SELECT COUNT(*)` per request. R1.05 discusses when that's too expensive and what `CursorPagination` does instead.

## Build

### 1. Replace the APIView

`api/views.py`:

```python
from django.db.models import QuerySet
from rest_framework import viewsets

from tracker.models import Project

from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Project]:
        return (
            Project.objects.filter(memberships__user=self.request.user)
            .select_related("owner")
            .order_by("name")
        )
```

- `lookup_field = "slug"`: the detail URL becomes `projects/{slug}/`, and `get_object()` filters `slug=<value>`. Public identifiers should be meaningful and stable; auto-increment IDs are neither.
- `.order_by("name")`: pagination over an unordered queryset gives inconsistent pages, and DRF warns (`UnorderedObjectListWarning`). `Meta.ordering` would cover it, but being explicit in the API is clearer.
- `create()` still works through `ProjectSerializer.create()` → `create_project`. `get_serializer()` passes `request` in the context automatically.

`api/urls.py`:

```python
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("projects", views.ProjectViewSet, basename="project")

urlpatterns = router.urls
```

Add the pagination settings above.

### 2. Explore

- In the browsable API: list, create, open a detail page, PATCH a description, DELETE a test project.
- `uv run python manage.py show_urls` doesn't exist without an extra package. Instead, in the shell: `from api.urls import router; [(str(p.pattern), p.name) for p in router.urls]`.
- Log in as a user who isn't a member of a project and GET its detail URL. You should get a 404.

### 3. Notice the hole

Log in as a plain *member* (not admin) of a project and PATCH its name. It works. Right now anyone in a project can rename or **delete** it. R1.03 fixes that with an object-level permission. Write down in `NOTES.md` where in the request flow you think the check should go before reading R1.03.

## Checkpoint

```bash
uv run pytest ../checkpoints/r1/test_r1_02_viewsets.py ../checkpoints/r1/test_r1_01_serializers.py
```

## Pitfalls

- **Class-level `queryset = Model.objects.all()` plus a forgotten `get_queryset` override** exposes everything.
- **Overriding `list()`/`retrieve()` to add scoping** instead of `get_queryset()`. Then `update` and `destroy` aren't scoped.
- **No pagination** on list endpoints.
- **Missing `basename`** without a class `queryset`: DRF fails at import time with an assertion telling you so.

## Explain it back

1. List every hook `ModelViewSet.partial_update` calls, in order, for `PATCH /api/projects/apollo/`.
2. Why does overriding only `get_queryset()` protect `destroy`?
3. What extra query does `PageNumberPagination` run, and when could it become the slowest part of a request?
4. Compare `ModelViewSet` with D1.06's `UpdateView`: which hooks correspond?
