# R1.03 — Authentication vs permissions; 401 vs 403 vs 404

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/r1/test_r1_03_auth_permissions.py`

## What you'll have at the end

- API clients authenticate with `Authorization: Token <key>`; browsers keep using their session.
- Anonymous requests get **401** with a `WWW-Authenticate` challenge.
- Members can read a project; only project **admins** can change or delete it (**403** for other members).
- Non-members get **404** everywhere.

## Concepts

### Two separate questions

DRF's `APIView.initial()` runs, before your handler:
1. **`perform_authentication`: who are you?** Each class in `authentication_classes` tries to identify the user from the request (a session cookie, a token header). The first one that returns a user wins. If none do, `request.user` is `AnonymousUser`. (Strictly, it's lazy: `request.user` triggers authentication on first access. `initial()` touches it, so it happens here.)
2. **`check_permissions`: may you do this, at all?** Each class in `permission_classes` has `has_permission(request, view)`. **All** of them must return `True`.
3. **`check_throttles`: are you doing it too often?** (R2.02.)

Then, *only when a handler calls `get_object()`*:

4. **`check_object_permissions`: may you do this, to this object?** Each permission's `has_object_permission(request, view, obj)` is called, and again all must pass.

### Object permissions are NOT checked on list views

`list` calls `get_queryset()` and serializes many objects. It never calls `get_object()`, so **`has_object_permission` never runs for lists or creates.** This is one of the most common DRF security bugs: someone writes a careful `has_object_permission`, sees the detail view return 403, and assumes lists are protected too. They aren't. That's why trackr scopes **in `get_queryset()`**. Object permissions here only distinguish admins from members *within* a project you can already see.

### Setting `permission_classes` replaces the default

```python
REST_FRAMEWORK = {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}

class ProjectViewSet(ModelViewSet):
    permission_classes = [IsProjectAdminOrReadOnly]     # ← IsAuthenticated is GONE for this view
```

A class attribute **replaces** the setting; it doesn't extend it. Anonymous users now pass `check_permissions` (your class has no `has_permission`, and `BasePermission.has_permission` returns `True`). Then they reach `get_queryset()`, which filters by an `AnonymousUser`. The result is a 500 at best, a data leak at worst. When this guide's reference implementation was first written, it had exactly this bug, and the checkpoint caught it. Always:

```python
permission_classes = [IsAuthenticated, IsProjectAdminOrReadOnly]
```

### 401 vs 403 vs 404

- **401 Unauthorized** really means *unauthenticated*: "I don't know who you are; here's how to tell me". It must carry a `WWW-Authenticate` header naming a scheme.
- **403 Forbidden**: "I know who you are, and you can't do this."
- **404**: "nothing here for you", which in trackr includes "exists, but you're not a member". Same reasoning as D1.04.

How does DRF choose between 401 and 403 for an anonymous request? It asks the **first** authentication class for a challenge (`authenticate_header`). `TokenAuthentication` returns `Token`, so you get a 401 with `WWW-Authenticate: Token`. `SessionAuthentication` returns nothing, because there's no standard challenge for cookies, so DRF falls back to 403. **The order of `DEFAULT_AUTHENTICATION_CLASSES` changes your status codes.** Put `TokenAuthentication` first.

### Sessions vs tokens, and CSRF again

- **Session auth** uses the browser's cookie, which the browser sends automatically. That's exactly what CSRF exploits. So DRF's `SessionAuthentication` **enforces CSRF** on unsafe methods for session-authenticated users, even though `APIView` itself is CSRF-exempt.
- **Token auth** uses a header the client must add itself. A forged cross-site request can't add it, so no CSRF token is needed. This is the answer to D1.05 "Explain it back" question 2.

`rest_framework.authtoken` is the simplest token scheme: one random 40-hex-character key per user, stored in the `authtoken_token` table, with no expiry. Know its limits:
- the key is stored **in plaintext**, so a database leak is a credential leak;
- there's only one token per user;
- there's no expiry or rotation.

For production, look at `django-rest-knox` (hashed, per-device, expiring tokens) or OAuth2/OIDC via a provider. JWTs (`djangorestframework-simplejwt`) are popular. Understand that their selling point (stateless verification) is also their weakness: you can't revoke one before it expires without reintroducing state.

## Build

### 1. Token auth

Settings:

```python
INSTALLED_APPS = [..., "rest_framework", "rest_framework.authtoken", ...]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
```

```bash
uv run python manage.py migrate        # creates authtoken_token
```

`api/urls.py`. Add a login endpoint that exchanges username and password for a token:

```python
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token"),
    *router.urls,
]
```

Try it:

```bash
curl -s -X POST localhost:8000/api/auth/token/ -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "..."}'
curl -s localhost:8000/api/projects/ -H "Authorization: Token <key>"
curl -si localhost:8000/api/projects/          # 401 + WWW-Authenticate: Token
```

Now swap the two authentication classes, repeat the last command, and see the 403. Swap back.

### 2. Your turn: `Project.is_admin` and `IsProjectAdminOrReadOnly`

**On the model:** `Project.is_admin(user) -> bool`. It's true if the user has an `admin`-role membership in this project. Use one query that doesn't load rows it doesn't need.

**In `api/permissions.py`:** `IsProjectAdminOrReadOnly(BasePermission)`.
- Safe methods (GET, HEAD, OPTIONS) are allowed for anyone who reached the object. They're already a member, because of `get_queryset()`.
- Unsafe methods require `obj.is_admin(request.user)`.
- Give it a `message` attribute. DRF uses it as the 403 detail text.

Then wire it into `ProjectViewSet` **without losing `IsAuthenticated`**.

The checkpoint's `test_permission_matrix` is the spec: admin, member and outsider × GET, PATCH and DELETE.

<details><summary>Hint 1</summary>

`rest_framework.permissions.SAFE_METHODS` is a tuple of the method names.
</details>

<details><summary>Hint 2</summary>

`.exists()` on a filtered `memberships` queryset is the cheapest "is there such a row" query.
</details>

<details><summary>Hint 3</summary>

Only implement `has_object_permission`. Why don't you need `has_permission` here? (What would it even check for a create, where there's no object yet?)
</details>

### 3. Your own tests

`tests/test_api_auth.py`: test that a *valid* session still works for GET, and that a POST with session auth **and without a CSRF token** is rejected with 403. Use `APIClient(enforce_csrf_checks=True)` with `client.force_login(user)`.

Know the difference between the two test shortcuts:
- `force_login` creates a real session. `SessionAuthentication` then authenticates it and enforces CSRF, which is what you want to test.
- `force_authenticate` (used by the checkpoints) **bypasses authentication classes entirely**, so CSRF never runs. Using it here would pass for the wrong reason.

Explain in a comment why this test matters.

## Checkpoint

```bash
uv run pytest ../checkpoints/r1/test_r1_03_auth_permissions.py
uv run pytest ../checkpoints/r1          # 01–03 together
```

## Pitfalls

- **`permission_classes = [MyPermission]` dropping `IsAuthenticated`** (see above).
- **Relying on `has_object_permission` for list endpoints.** It never runs there.
- **Returning 403 for objects the user can't see**, which leaks existence. Scope with `get_queryset` instead.
- **Session auth first in `DEFAULT_AUTHENTICATION_CLASSES`.** Anonymous API clients get 403s without a challenge, and well-behaved clients don't know to authenticate.
- **Logging `Authorization` headers.** Treat tokens like passwords.

## Explain it back

1. Explain the four checks in `APIView.initial()` and `get_object()`, in order, and say which ones run for a `list`.
2. Walk an anonymous `GET /api/projects/apollo/` through a ViewSet whose `permission_classes = [IsProjectAdminOrReadOnly]` only. Where exactly does it fail?
3. Why does the order of authentication classes change the status code for anonymous requests?
4. Why does session auth need CSRF protection and token auth not? What would change if your SPA stored the token in a cookie?
