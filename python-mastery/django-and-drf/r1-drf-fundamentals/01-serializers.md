# R1.01 — Serializers, and the first endpoint

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/r1/test_r1_01_serializers.py`

## What you'll have at the end

`GET /api/projects/` lists your projects as JSON. `POST /api/projects/` creates one, through the `create_project` service, with you as owner and admin. All of it goes through a `ProjectSerializer` that decides exactly which fields go in and out.

## Concepts

### Two directions, two methods

A serializer converts both ways:
- **Output:** `serializer.data` calls `to_representation(instance)`, which turns a model instance into a dict of primitives that the renderer turns into JSON.
- **Input:** `serializer.is_valid()` calls `to_internal_value(data)` and then validation, turning untrusted primitives into `validated_data` of Python values.

```python
ProjectSerializer(project).data                     # output: {'slug': 'apollo', ...}
s = ProjectSerializer(data={"name": "X", "slug": "x"})
s.is_valid()                                        # input
s.validated_data                                    # {'name': 'X', 'slug': 'x'}
s.save()                                            # → self.create(validated_data)
```

- `save()` calls `create()` if the serializer was built without an instance, or `update(instance, validated_data)` if it was built with one.
- Extra keyword arguments to `save(**kwargs)` are merged into `validated_data`. That's the usual way to inject server-owned values like `owner=request.user`.

### Validation order

Like a form:
1. each field's `to_internal_value` (type conversion, `max_length`, choices, …);
2. `validate_<field>(value)` methods;
3. `validate(attrs)` for cross-field rules;
4. **model-derived validators**: `ModelSerializer` adds `UniqueValidator` for `unique=True` fields and `UniqueTogetherValidator` for unique constraints whose fields are *all* writable.

Errors come back as `{"field": ["message", ...]}` with status 400 when you use `is_valid(raise_exception=True)`.

### `ModelSerializer`: derived, and allow-listed

`ModelSerializer` reads the model and builds fields for you, much like `ModelForm`. **Always list `fields` explicitly.** `fields = "__all__"` is mass assignment again, and it also *leaks* every new column (internal counters, flags) the day someone adds one. The checkpoint fails if `next_issue_number` appears in the output.

Field options you'll use constantly:
- `read_only_fields = [...]`, or `read_only=True` on a declared field: shown in output, ignored in input. Clients can send them and nothing happens. That's the correct behaviour, not an error.
- `write_only=True`: accepted on input, never shown (passwords).
- **Relations.** By default an FK is represented by its primary key. That leaks database IDs and makes the API awkward. `SlugRelatedField(slug_field="username", read_only=True)` shows `"ada"` instead of `7`.

### `context`

A serializer is a plain object; it doesn't know about the request. Views pass `context={"request": request, ...}` and serializers read `self.context["request"].user`. DRF's generic views do it for you through `get_serializer_context()` (R1.02). R1.04 puts the current project in the context too.

### `APIView`: Django's `View` with API plumbing

`APIView` subclasses Django's `View` and adds:
- a `Request` wrapper (`request.data` for parsed bodies of any content type);
- `Response` plus content negotiation (JSON for clients, the browsable API for browsers);
- authentication → permissions → throttling *before* your handler runs;
- exception handling that turns `ValidationError`, `NotFound`, `PermissionDenied`, … into proper status codes and JSON bodies.

It's also **CSRF-exempt at the Django level**. DRF's `SessionAuthentication` re-enforces CSRF for session-cookie users itself; R1.03 explains why.

## Build

### 1. Install and wire

`django-and-drf/pyproject.toml` already lists `djangorestframework`. Create the app **first**. `manage.py` loads your settings before doing anything, so if `"api"` is already in `INSTALLED_APPS` it fails with `ModuleNotFoundError: No module named 'api'`:

```bash
uv run python manage.py startapp api
```

Then, in `config/settings.py`:

```python
INSTALLED_APPS = [
    ...,
    "rest_framework",
    "accounts",
    "tracker",
    "api",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
```

DRF's out-of-the-box default permission is `AllowAny`. **Set `IsAuthenticated` globally on day one**, so a forgotten permission fails closed.

Delete `api/models.py`, `api/admin.py`, `api/tests.py`, and the `migrations/` folder: this app has no models. `config/urls.py` gets `path("api/", include("api.urls"))` *before* the `""` include.

### 2. Get a feel for it in the shell

```python
from rest_framework import serializers

class Tiny(serializers.Serializer):
    name = serializers.CharField(max_length=5)
    stars = serializers.IntegerField(min_value=0)

s = Tiny(data={"name": "toolong", "stars": "-3"})
s.is_valid(); s.errors
s = Tiny(data={"name": "ok", "stars": "3"})
s.is_valid(); s.validated_data        # note: "3" became 3
```

### 3. `api/serializers.py`

```python
from typing import Any

from rest_framework import serializers

from tracker.models import Project
from tracker.services import create_project


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Project
        fields = ["slug", "name", "description", "owner", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data: dict[str, Any]) -> Project:
        return create_project(owner=self.context["request"].user, **validated_data)
```

- **`create()` delegates to the service** you wrote in D2.04. The API and the HTML views now share one definition of "create a project". Without it you'd have a project with no admin membership, which nobody could ever manage.
- `slug` is writable and `unique=True` on the model, so `ModelSerializer` adds a `UniqueValidator` automatically. A duplicate slug is a 400, not a 500.
- `owner` is read-only. A client sending `"owner": "someone"` is ignored, not rejected. Read the checkpoint's `test_owner_cannot_be_set_by_the_client`.

### 4. Your turn: reserved slugs

Add field-level validation so the slugs `new`, `admin` and `api` are rejected with a clear message. They'd collide with URL paths you own or will own. The error must be reported on the `slug` field.

<details><summary>Hint</summary>

Validation step 2 above. The method receives the already-converted value and returns it (possibly modified) or raises `serializers.ValidationError`.
</details>

### 5. `api/views.py`

```python
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tracker.models import Project

from .serializers import ProjectSerializer


class ProjectListCreate(APIView):
    def get(self, request: Request) -> Response:
        projects = Project.objects.filter(memberships__user=request.user).select_related("owner")
        return Response(ProjectSerializer(projects, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ProjectSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

- `many=True` wraps the serializer in a `ListSerializer` that serializes each item.
- `select_related("owner")`: the serializer reads `project.owner.username` for every project. That's N+1 again, in JSON form.
- The membership scoping is the same rule as D1.04, written again. R1.02 fixes the duplication.

`api/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("projects/", views.ProjectListCreate.as_view(), name="project-list"),
]
```

The name `project-list` is what DRF's router will generate in R1.02, so the checkpoint keeps passing after you switch.

### 6. Use the browsable API

Log into `/admin/`, then open http://127.0.0.1:8000/api/projects/. POST a project from the form at the bottom. Then POST a duplicate slug, a reserved slug, and one with an `owner` field.

## Checkpoint

```bash
uv run pytest ../checkpoints/r1/test_r1_01_serializers.py
```

## Pitfalls

- **`fields = "__all__"` or `exclude = [...]`.** Both expose new columns by default. Allow-list.
- **Doing writes in the view** (`Project.objects.create(...)`) instead of `serializer.save()` → service. You lose validation and duplicate the business rules.
- **Forgetting `context={"request": request}`** when instantiating serializers by hand. `self.context["request"]` raises `KeyError`. Generic views pass it for you.
- **Treating `read_only` fields in the input as errors.** DRF ignores them by design.

## Explain it back

1. Trace `POST /api/projects/` with `{"name": "Apollo", "slug": "api"}` through `APIView.dispatch`, the serializer's validation steps and the response. Which step rejects it, and what's the response body?
2. A client sends `"owner": "someone"`. Why is ignoring it better than rejecting it with a 400? Can you think of a case where rejecting would be better?
3. In what sense is a serializer "a form for JSON"? Name two differences from `ModelForm`.
4. Why set `IsAuthenticated` as the global default rather than per view?
