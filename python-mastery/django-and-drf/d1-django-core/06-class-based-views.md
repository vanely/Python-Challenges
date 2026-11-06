# D1.06 — Class-based views: reading a framework through its MRO

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/d1/test_d1_06_cbv.py`

## What you'll have at the end

- The project list and detail pages rewritten as generic class-based views (CBVs).
- An issue edit page built on `UpdateView`.

More importantly, you'll be able to open any CBV and predict which methods run and in what order. DRF is built entirely on this pattern.

## Concepts

### Why CBVs exist

Your function views repeat a shape: fetch a queryset, maybe one object, build a context, render a template. Generic CBVs package that shape into **small overridable methods**. You change one step without rewriting the rest. The cost is indirection: the code that runs is spread over five mixins. You don't learn CBVs by memorising them, you learn to *read* them.

### `as_view()` and `dispatch()`

URLconfs need a function, so `ProjectListView.as_view()` returns one. On each request that function:
1. creates a **new instance** of the class (so per-request state on `self` is safe);
2. sets `self.request`, `self.args`, `self.kwargs`;
3. calls `self.dispatch(request, ...)`, which calls `self.get()` or `self.post()` based on the HTTP method (or returns 405).

The view function remembers its class in `.view_class`. The checkpoint uses that to check you used the right base.

### The MRO is the documentation

```python
class ProjectListView(LoginRequiredMixin, ListView): ...
```

Python's method resolution order (MRO), computed by the C3 linearisation algorithm, decides which `dispatch` runs first. `super()` means "the next class in the *instance's* MRO", not "my parent":

```python
>>> [c.__name__ for c in ProjectListView.__mro__]
['ProjectListView', 'LoginRequiredMixin', 'AccessMixin', 'ListView',
 'MultipleObjectTemplateResponseMixin', 'TemplateResponseMixin',
 'BaseListView', 'MultipleObjectMixin', 'ContextMixin', 'View', 'object']
```

- `LoginRequiredMixin.dispatch` runs *before* `View.dispatch` and short-circuits anonymous users.
- **That's why mixins go on the left.** `class V(ListView, LoginRequiredMixin)` linearises to `V, ListView, …, View, LoginRequiredMixin, AccessMixin, object`. `View.dispatch` comes first and never calls `super().dispatch()`, so the login check silently never runs.

### What `ListView.get` actually does

Open https://ccbv.co.uk/projects/Django/6.1/django.views.generic.list/ListView/ (pick the newest version listed if 6.1 isn't there yet) and follow `get()`:

```
get()
 ├─ self.object_list = self.get_queryset()        ← override to scope data
 ├─ context = self.get_context_data()             ← override to add extra context
 │     └─ paginate_queryset(), context_object_name …
 └─ return self.render_to_response(context)
       └─ get_template_names()                    ← template_name, or "<app>/<model>_list.html"
```

`DetailView.get` is the same, with `self.object = self.get_object()` in place of `get_queryset()`. And `get_object()` *calls `get_queryset()`* and filters by the URL's `pk` or `slug`. **So overriding `get_queryset()` to scope by membership protects the detail view too.** It's the CBV form of D1.04's scoped lookup.

`UpdateView`, for editing, adds a form:
- **`get`**: `get_object()`, then a form bound to that instance, then render.
- **`post`**: `get_object()`, then the form bound to `request.POST` and the instance, then `form_valid()` or `form_invalid()`.
- **`form_valid`**: `form.save()`, then redirect to `get_success_url()`. That defaults to `self.object.get_absolute_url()`.
- **`get_form_kwargs()`** builds the constructor arguments for the form (`data`, `files`, `instance`, `initial`). It's the hook for passing extra ones like `project=`.

### When to use which

- **Function views** when the view is unusual, or several forms and objects interact. Explicit beats clever.
- **Generic CBVs** when the view *is* a list, detail, create, update or delete page with a twist. Override one or two hooks, done.
- Teams split on this. Read both fluently. DRF's generic views (R1.02) are the same idea with JSON instead of templates.

## Build

### 1. Convert list and detail

Replace `project_list` and `project_detail` in `tracker/views.py`:

```python
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView


class ProjectListView(LoginRequiredMixin, ListView):
    template_name = "tracker/project_list.html"
    context_object_name = "projects"

    def get_queryset(self) -> QuerySet[Project]:
        return member_projects(self.request)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    template_name = "tracker/project_detail.html"
    context_object_name = "project"

    def get_queryset(self) -> QuerySet[Project]:
        return member_projects(self.request)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["issues"] = self.object.issues.select_related("assignee")
        return context
```

`tracker/urls.py`:

```python
    path("", views.ProjectListView.as_view(), name="project_list"),
    path("p/<slug:slug>/", views.ProjectDetailView.as_view(), name="project_detail"),
```

`DetailView` finds the object by the URL kwarg named `slug` (its `slug_url_kwarg`) matched against the model field `slug` (its `slug_field`). Your URL already uses that name, so nothing else changes. The templates don't change either, because you kept the context names.

Run the D1.04 checkpoint again: it must still pass. **Refactors are verified by the old tests.**

```bash
uv run pytest ../checkpoints/d1/test_d1_04_views.py
```

### 2. Print the MRO

In `uv run python manage.py shell`:

```python
from tracker.views import ProjectListView
[c.__name__ for c in ProjectListView.__mro__]
```

Now swap the bases to `(ListView, LoginRequiredMixin)`, reload the page logged out, and see what happens. Then swap them back.

Here you'll get a **500**, not a login redirect: `TypeError: Field 'id' expected a number but got <AnonymousUser…>`, raised from `member_projects`. The login check never ran. Your queryset happened to crash on the anonymous user, and that's luck. A view whose queryset doesn't touch `request.user`, like a public list with a members-only template block, would render silently for anyone. That silent version is the real risk with mixin order.

### 3. Your turn: `IssueUpdateView`

URL: `p/<slug:slug>/issues/<int:number>/edit/`, named `issue_update`, using `UpdateView`. Requirements:
- login required; non-members get 404 on both GET and POST;
- uses `IssueForm`, so the assignee queryset is still restricted to project members;
- reuses `tracker/issue_form.html` (the template needs `project` in its context);
- after saving, redirects to the issue page;
- the issue's number never changes;
- add an "Edit" link on the issue page.

<details><summary>Hint 1: finding the object</summary>

The URL has two kwargs, neither of them `pk`. That's more than `slug_field`/`slug_url_kwarg` can express. Override `get_object()` and use the same scoped lookup as your `issue_detail` view. `self.kwargs` holds the URL arguments.
</details>

<details><summary>Hint 2: the form's extra argument</summary>

`IssueForm.__init__` requires `project=`. Find the method in the `UpdateView` flow above that builds the form's constructor arguments, call `super()`, and add one key.
</details>

<details><summary>Hint 3: redirect</summary>

You don't need `success_url`. Why not? (Look at what `get_success_url` does when it's unset.)
</details>

## Checkpoint

```bash
uv run pytest ../checkpoints/d1/test_d1_06_cbv.py
uv run pytest ../checkpoints/d1          # all of D1 must still be green
uv run ruff check .
```

## Pitfalls

- **Mixin order** (see the MRO section).
- **Overriding `get()` instead of a hook**, and losing the behaviour you inherited (pagination, context, template resolution).
- **Setting `queryset = Project.objects.all()` as a class attribute and scoping in the template.** `get_object()` would find any project.
- **Storing state on the class instead of `self`.** Class attributes are shared by every request. `self` is per-request.

## Explain it back

1. List the methods that run, in order, for a GET to `ProjectDetailView`, from `as_view()` to the rendered response.
2. Why does overriding only `get_queryset()` protect `DetailView` from showing non-members' projects?
3. Explain why `class V(ListView, LoginRequiredMixin)` silently skips the login check, using the MRO.
4. Retrospective for D1 in `NOTES.md`: what did Django do for you that you would have hand-written in Express or FastAPI? What did it make *harder*?

## Read the source (optional)

`django/views/generic/base.py` (`View.as_view`, `View.dispatch`) and `django/views/generic/detail.py` (`SingleObjectMixin.get_object`). About 150 lines together, and the whole CBV system rests on them.
