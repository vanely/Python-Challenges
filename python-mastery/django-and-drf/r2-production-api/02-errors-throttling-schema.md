# R2.02 — One error shape, throttling, and an OpenAPI schema

**Time:** ~3 h · **Checkpoint:** `uv run pytest ../checkpoints/r2/test_r2_02_errors_schema.py`

## What you'll have at the end

- Every error response has the shape `{"error": {"code", "message", "details"}}`.
- The token endpoint allows 5 attempts per minute per client.
- `/api/schema/` serves an OpenAPI 3 document, `/api/docs/` serves Swagger UI, and schema generation passes with **zero warnings**.

## Concepts

### Why an error envelope

Out of the box, DRF errors come in several shapes:
- `{"detail": "Not found."}` for most exceptions;
- `{"title": ["This field is required."]}` for validation;
- `["Some message"]` for a non-field `ValidationError` raised with a string.

A TypeScript client has to sniff the shape. One envelope makes error handling one code path:

```json
{"error": {"code": "not_found", "message": "Not found.", "details": null}}
{"error": {"code": "invalid", "message": "Invalid input.", "details": {"slug": ["Enter a valid slug..."]}}}
```

- `code` is stable and machine-readable (clients switch on it).
- `message` is for humans.
- `details` carries field errors for validation, and `null` otherwise.

### How DRF exception handling works

When a handler raises, `APIView.handle_exception` calls the function named in `EXCEPTION_HANDLER`. The default `rest_framework.views.exception_handler`:
1. converts Django's `Http404` into DRF's `NotFound`, and Django's `PermissionDenied` into DRF's `PermissionDenied`;
2. for any `APIException`, builds a `Response(exc.detail, status=exc.status_code)` and copies `WWW-Authenticate`/`Retry-After` headers;
3. for anything else, returns `None`, which means "not mine". Django then turns it into a 500 (and, with `DEBUG` off, your error logging sees it).

Your handler wraps the default one and reshapes `response.data`. One trap: the conversion in step 1 happens *inside* the default handler, on a local variable. Your code still holds the original `Http404`, which has no DRF `code`. Do the same conversion yourself first, so `code` comes out as `"not_found"` rather than a generic fallback. The checkpoint tests exactly this case.

`APIException.get_codes()` returns the machine code(s). `exc.detail` carries `ErrorDetail` strings, each with a `.code`.

### Throttling: what it is and isn't

DRF throttles count requests per key (user ID, or client IP for anonymous requests) in **Django's cache**, and return **429** with `Retry-After` once a rate is exceeded.

- **`ScopedRateThrottle`** applies the rate named by the view's `throttle_scope` (`"auth": "5/min"` in settings).
- **The default cache is `LocMemCache`: per process.** With 4 gunicorn workers, "5/min" is really up to "20/min". In production, point `CACHES` at Redis or Memcached, or the throttle is a suggestion.
- **Client IP comes from `REMOTE_ADDR`, or `X-Forwarded-For` if `NUM_PROXIES` is set.** Behind a load balancer without that setting, *every* client shares the balancer's IP and one user can throttle everyone. Set `NUM_PROXIES` correctly, never higher: clients can forge extra `X-Forwarded-For` entries.
- **Throttling is not authentication security.** It slows naive credential stuffing from one IP; it doesn't stop a botnet. Real defences add account lockout or backoff, breached-password checks (Django's `CommonPasswordValidator` is a start), and MFA.

### OpenAPI with drf-spectacular

`drf-spectacular` introspects your ViewSets, serializers, FilterSets and pagination, and emits an OpenAPI 3 schema. Clients generate TypeScript types from it (`openapi-typescript`), so the schema becomes the contract between backend and frontend. That's the same role FastAPI's built-in schema played in Stage 1.

To build the schema, spectacular **instantiates your views with a fake request** and calls `get_queryset()` to learn the model. Your `get_queryset()` filters by `request.user`, which is anonymous during generation, and `IssueViewSet.project` needs a `project_slug` that doesn't exist. Generation then warns. Without the model it can't type the `{number}` path parameter either. The standard fix:

```python
def get_queryset(self):
    if getattr(self, "swagger_fake_view", False):
        return Issue.objects.none()
    ...
```

Spectacular sets `swagger_fake_view = True` on the views it instantiates. Returning an empty queryset of the right model tells it everything it needs. Use the same guard anywhere you touch `self.project` during schema generation (`get_serializer_context`).

**Run `spectacular --validate --fail-on-warn` in CI.** A warning means the schema is wrong somewhere, and a wrong schema means wrong generated client types.

## Build

### 1. The exception handler: `api/exceptions.py`

```python
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler


def envelope_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is None or not isinstance(exc, exceptions.APIException):
        return response

    if isinstance(exc, exceptions.ValidationError):
        code, message, details = "invalid", "Invalid input.", response.data
    else:
        code, message, details = exc.get_codes(), str(exc.detail), None

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
```

Converting `Http404` to a fresh `NotFound()` replaces Django's message ("No Project matches the given query.") with DRF's generic "Not found.". That's arguably better: it doesn't echo model names to clients.

Settings:

```python
REST_FRAMEWORK = {
    ...,
    "EXCEPTION_HANDLER": "api.exceptions.envelope_exception_handler",
}
```

Earlier checkpoints that inspect error bodies (R1.04) were written to accept both shapes, so they stay green.

### 2. Your turn: throttle the token endpoint

Replace `obtain_auth_token` with a subclass of `rest_framework.authtoken.views.ObtainAuthToken` that applies a scoped throttle named `auth`, and set that rate to `5/min` in settings (`DEFAULT_THROTTLE_RATES`). The URL name stays `api-token`.

Requirements, from the checkpoint:
- five wrong-password attempts return 400;
- the sixth returns 429, in the envelope, with a `Retry-After` header.

<details><summary>Hint 1</summary>

`ObtainAuthToken` is an `APIView`. Throttling is configured with two class attributes. One of them must *replace* the (empty) default list. Remember R1.03's "a class attribute replaces the setting".
</details>

<details><summary>Hint 2</summary>

`DEFAULT_THROTTLE_RATES` maps scope names to rates. It's read when throttles are instantiated.
</details>

### 3. OpenAPI

Settings:

```python
INSTALLED_APPS = [..., "drf_spectacular", ...]

REST_FRAMEWORK = {
    ...,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "trackr API",
    "VERSION": "1.0.0",
}
```

`api/urls.py`:

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("auth/token/", views.ThrottledObtainAuthToken.as_view(), name="api-token"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    *router.urls,
]
```

(The `ThrottledObtainAuthToken` name is a suggestion. Use whatever you named your class in step 2.)

Now generate the schema and read the warnings:

```bash
uv run python manage.py spectacular --validate --file schema.yml
```

Fix every warning with the `swagger_fake_view` guard described above, until this passes:

```bash
uv run python manage.py spectacular --validate --fail-on-warn --file schema.yml
```

Open http://127.0.0.1:8000/api/docs/ and try the endpoints from Swagger UI with your token ("Authorize" button, value `Token <key>`).

Optional: generate TypeScript types to see the contract in action:

```bash
npx openapi-typescript schema.yml -o trackr-api.d.ts
```

## Checkpoint

```bash
uv run pytest ../checkpoints/r2/test_r2_02_errors_schema.py
uv run pytest ../checkpoints/r1            # envelope must not break R1
```

## Pitfalls

- **Reshaping errors without converting `Http404` first.** `code` comes out wrong for every 404 from `get_object_or_404`.
- **Swallowing non-API exceptions** in the handler (`return Response(...)` for everything). Real 500s become fake 200s or 400s, and your error tracking goes blind.
- **LocMemCache throttles in multi-process deployments.**
- **Ignoring schema warnings.** Each one is a wrong type in some client.

## Explain it back

1. Trace `GET /api/projects/nope/` from `get_object_or_404` to the final JSON, naming each function that touches the exception.
2. Your API runs as 4 processes on 3 machines behind a load balancer, with the default cache and no `NUM_PROXIES`. What does "5/min" actually mean? Fix both problems.
3. Why does drf-spectacular need `swagger_fake_view`, and what would it document wrongly without it?
