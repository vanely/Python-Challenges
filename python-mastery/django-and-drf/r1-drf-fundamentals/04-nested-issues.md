# R1.04 — A nested resource, scoped relations, and state changes as actions

**Time:** ~3 h · **Checkpoint:** `uv run pytest ../checkpoints/r1/test_r1_04_issues.py`

## What you'll have at the end

```
GET   /api/projects/{slug}/issues/               list
POST  /api/projects/{slug}/issues/               create (number + reporter assigned by the server)
GET   /api/projects/{slug}/issues/{number}/      retrieve
PATCH /api/projects/{slug}/issues/{number}/      edit title/body/priority/assignee/labels
POST  /api/projects/{slug}/issues/{number}/close/
POST  /api/projects/{slug}/issues/{number}/reopen/
```

There's no DELETE. Status changes only happen through the actions.

## Concepts

### Nested URLs without a nested-router library

Issues only make sense inside a project, and their public ID (`number`) is only unique per project. So the URL carries both. DRF's router accepts a **regex prefix with a named group**:

```python
router.register(r"projects/(?P<project_slug>[-\w]+)/issues", IssueViewSet, basename="project-issue")
```

The captured `project_slug` ends up in `self.kwargs`, alongside `number` for detail routes. The `drf-nested-routers` package automates this for deep trees. For one level, the plain router is clearer.

### Load the parent once, scoped

Every request needs "the project in the URL, if I'm a member". Define it once on the ViewSet:

```python
@cached_property
def project(self) -> Project:
    return get_object_or_404(
        Project.objects.filter(memberships__user=self.request.user), slug=self.kwargs["project_slug"]
    )
```

- `functools.cached_property` computes once **per instance**, and DRF creates one ViewSet instance per request. So it's one query per request, never shared between users.
- A non-member hits the 404 here, on *every* route, including `create`, which has no object to check permissions on.

### Scoping *inputs*: the relation querysets

D1.05's lesson, in its most important form. An issue's `assignee` must be a member of *this* project, and its `labels` must belong to *this* project. A `SlugRelatedField` validates input by looking the slug up in its `queryset`. If that queryset is `User.objects.all()`:
- anyone can assign issues to any user on the platform;
- **the 400 vs 201 response becomes an oracle** that tells an attacker which usernames exist.

The queryset depends on the request (which project?), so it can't be fixed at class-definition time. Set it per instance in `get_fields()`, from the serializer's context:

```python
def get_fields(self):
    fields = super().get_fields()
    project = self.context.get("project")
    if project is not None:
        fields["assignee"].queryset = project.members.all()
        fields["labels"].child_relation.queryset = project.labels.all()
    return fields
```

- `many=True` wraps the field in a `ManyRelatedField`, so the queryset lives on its `child_relation`.
- The class-level `queryset=X.objects.none()` makes the safe default "accept nothing". Forgetting the context fails closed.

### Server-owned fields

`number`, `status`, `reporter`, `created_at`, `updated_at` and `closed_at` are all read-only to clients:
- `number` and `reporter` are assigned by the server (`create_issue`);
- `status` and `closed_at` can only change together, which the database constraint from D1.02 enforces. If `status` were writable via PATCH, `{"status": "closed"}` would violate the constraint and give you a 500. So status changes are **actions**, which call the model's `close()`/`reopen()` and keep the invariant.

### Extra actions

```python
@action(detail=True, methods=["post"])
def close(self, request, project_slug, number): ...
```

- `detail=True` routes to `issues/{number}/close/`.
- The router names it `project-issue-close`.
- Inside it, `self.get_object()` gives you the same scoping and object permissions as `retrieve`.

Use actions for **state transitions that aren't "edit some fields"**: close, approve, archive, resend. That's better than making clients PATCH a status field and hoping the side effects follow.

### Why `http_method_names` and not just "don't implement destroy"

`ModelViewSet` includes `DestroyModelMixin`. Listing `http_method_names = ["get", "post", "patch", "head", "options"]` makes DELETE (and PUT) return **405 Method Not Allowed**. The browsable API and the OpenAPI schema stop offering them too. (Issue history matters, so close, don't delete.)

## Build

### 1. `IssueSerializer` (in `api/serializers.py`)

```python
from django.contrib.auth import get_user_model

from tracker.models import Issue, Label, Project
from tracker.services import create_issue, create_project

User = get_user_model()


class IssueSerializer(serializers.ModelSerializer):
    reporter = serializers.SlugRelatedField(slug_field="username", read_only=True)
    assignee = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.none(), allow_null=True, required=False
    )
    labels = serializers.SlugRelatedField(
        slug_field="name", many=True, queryset=Label.objects.none(), required=False
    )

    class Meta:
        model = Issue
        fields = [
            "number",
            "title",
            "body",
            "status",
            "priority",
            "reporter",
            "assignee",
            "labels",
            "created_at",
            "updated_at",
            "closed_at",
        ]
        read_only_fields = ["number", "status", "created_at", "updated_at", "closed_at"]

    def get_fields(self) -> dict[str, Any]:
        fields = super().get_fields()
        project: Project | None = self.context.get("project")
        if project is not None:
            fields["assignee"].queryset = project.members.all()
            fields["labels"].child_relation.queryset = project.labels.all()
        return fields

    def create(self, validated_data: dict[str, Any]) -> Issue:
        return create_issue(
            project=self.context["project"],
            reporter=self.context["request"].user,
            **validated_data,
        )
```

`create()` hands everything to the D2.04 service: the lock, the numbering and the labels. There's no `update()` override, because `ModelSerializer.update()` sets attributes, saves, and sets M2M fields itself. Editing doesn't involve numbering.

### 2. `IssueViewSet` (in `api/views.py`)

```python
from functools import cached_property

from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from tracker.models import Issue, Project

from .serializers import IssueSerializer, ProjectSerializer


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    lookup_field = "number"
    http_method_names = ["get", "post", "patch", "head", "options"]

    @cached_property
    def project(self) -> Project:
        return get_object_or_404(
            Project.objects.filter(memberships__user=self.request.user),
            slug=self.kwargs["project_slug"],
        )

    def get_queryset(self) -> QuerySet[Issue]:
        return (
            Issue.objects.filter(project=self.project)
            .select_related("reporter", "assignee")
            .prefetch_related("labels")
            .order_by("-number")
        )

    def get_serializer_context(self) -> dict[str, object]:
        context = super().get_serializer_context()
        context["project"] = self.project
        return context

    @action(detail=True, methods=["post"])
    def close(self, request: Request, project_slug: str, number: str) -> Response:
        issue = self.get_object()
        if issue.status != Issue.Status.CLOSED:
            issue.close()
            issue.save(update_fields=["status", "closed_at", "updated_at"])
        return Response(self.get_serializer(issue).data)
```

- **`select_related` + `prefetch_related` in `get_queryset`**: the serializer touches reporter, assignee and labels for every issue. This is D2.02, and R2.01 makes you prove it with a query-count test.
- **`update_fields` includes `updated_at`.** `auto_now` fields are only bumped when they're in `update_fields` (or when you save without `update_fields`).
- **`close` is idempotent.** Closing a closed issue returns 200 with the current state and doesn't move `closed_at`. Retries from flaky mobile networks are harmless.
- `create()` needs no override. `CreateModelMixin` calls `serializer.save()`, which calls your `IssueSerializer.create()`, which reads the project from the context.

Register it in `api/urls.py`:

```python
router.register(
    r"projects/(?P<project_slug>[-\w]+)/issues", views.IssueViewSet, basename="project-issue"
)
```

### 3. Your turn: `reopen`

Add a `reopen` action: `POST .../issues/{number}/reopen/`. It returns the issue, idempotent in the same way, keeping the `closed_at` invariant via the model method. URL name `project-issue-reopen`.

### 4. Your own tests

`tests/test_api_issues.py`:
- A member can PATCH `labels` to `[]`, and the labels are actually removed. M2M updates are the classic thing to get wrong.
- PATCHing `{"status": "closed"}` changes nothing and returns 200. Why 200 and not 400? Write the answer in the test's docstring.
- Two issues created in two different projects both get number 1.

## Checkpoint

```bash
uv run pytest ../checkpoints/r1/test_r1_04_issues.py
uv run pytest ../checkpoints/d2/test_d2_04_transactions.py   # the service is shared; still green?
```

## Pitfalls

- **`queryset=User.objects.all()` on input relations.** Data integrity bug *and* user-enumeration oracle.
- **Writable `status`** next to a database invariant that needs two fields to change together.
- **Loading the project in several places with different scoping.** Have exactly one `project` property.
- **Storing per-request state on the class** (`IssueViewSet.project = ...`). It would be shared across concurrent requests. Instance attributes or `cached_property` only.
- **Forgetting `prefetch_related("labels")`.** The list endpoint goes N+1.

## Explain it back

1. Explain the user-enumeration oracle with a concrete pair of requests and responses.
2. Why is `status` read-only, and why are transitions actions instead?
3. `cached_property` on a ViewSet: why is it safe, and when would the same decorator be dangerous?
4. What does DRF return for `DELETE .../issues/1/` and why? What does a client learn from that response that it wouldn't learn from a 404?
