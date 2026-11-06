# R1 — Django REST Framework fundamentals

Same database, same models, same services. A second interface on top: a JSON API that a mobile app or a TypeScript SPA could use. You'll put it in its own app, `api`, so the boundary is visible: **`tracker` owns the domain, `api` and the views own the interfaces.**

## The mapping from what you know

| Plain Django (D1) | DRF (R1) | FastAPI (Stage 1) |
|---|---|---|
| `HttpRequest`, `request.POST` | `Request`, `request.data` (parsed JSON/form/multipart) | typed function params / Pydantic body |
| `HttpResponse`, `render()` | `Response(data)`, content negotiation picks JSON or the browsable HTML | return a model/dict |
| `forms.ModelForm` | `serializers.ModelSerializer` | Pydantic model |
| function view / `View` | `APIView` / `@api_view` | path operation function |
| generic CBVs | generic API views + mixins, `ViewSet` | — |
| URLconf by hand | `Router` generating URLs from ViewSets | `APIRouter` |
| `@login_required`, scoping querysets | authentication classes + permission classes + scoped `get_queryset` | `Depends(get_current_user)` |

If you take one thing from this table: **a serializer is a form whose input and output are JSON.** Everything you learned in D1.05 about validation, allow-listed fields and scoped choice querysets applies directly.

## Steps

| Step | File | You build | Checkpoint |
|---|---|---|---|
| 1 | [01-serializers.md](01-serializers.md) | `ProjectSerializer`, a list/create endpoint with `APIView` | `test_r1_01_serializers.py` |
| 2 | [02-viewsets-routers.md](02-viewsets-routers.md) | `ProjectViewSet`, a router, pagination | `test_r1_02_viewsets.py` |
| 3 | [03-auth-permissions.md](03-auth-permissions.md) | Token auth, 401 vs 403 vs 404, an object-level permission | `test_r1_03_auth_permissions.py` |
| 4 | [04-nested-issues.md](04-nested-issues.md) | `/projects/{slug}/issues/{number}/`, scoped relations, `close`/`reopen` actions | `test_r1_04_issues.py` |
| 5 | [05-filtering-pagination.md](05-filtering-pagination.md) | Filtering, search, ordering, and why the ordering allow-list is security | `test_r1_05_filtering.py` |

## Tooling

- The **browsable API**: open http://127.0.0.1:8000/api/projects/ while logged in to the admin (session auth). DRF renders an HTML page where you can GET and POST. Use it constantly.
- From the terminal, use `curl` or [HTTPie](https://httpie.io/) (`uv tool install httpie`): `http :8000/api/projects/ "Authorization: Token <key>"`.

## Done means

- `uv run pytest ../checkpoints/d1 ../checkpoints/d2 ../checkpoints/r1` is green. Plain `../checkpoints` also collects R2, which can't pass yet.
- You have tests of your own in `trackr/tests/` for every endpoint, using `APIClient`. At minimum: one happy path, one validation failure and one permission failure each.
- `NOTES.md`: every "Explain it back" answer, plus a retrospective. Compare writing the same endpoint in FastAPI and DRF: what did each make easy, and what did each hide?
