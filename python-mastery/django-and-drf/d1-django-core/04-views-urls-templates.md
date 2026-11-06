# D1.04 — URLs, views, templates, and "who is asking?"

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/d1/test_d1_04_views.py`

## What you'll have at the end

- A login page.
- A project list showing only *your* projects.
- A project page listing its issues.
- An issue page at `/p/<slug>/issues/<number>/`.
- Anyone who isn't a member gets a 404 everywhere.

## Concepts

### URLconfs: routing is a list, tried in order

```python
urlpatterns = [
    path("p/<slug:slug>/", views.project_detail, name="project_detail"),
]
```

- `path()` patterns use **converters**: `<int:number>` matches digits and passes an `int`; `<slug:slug>` matches `[-a-zA-Z0-9_]+`. The captured values arrive as keyword arguments to the view.
- `include("tracker.urls")` mounts another list under a prefix.
- **`name=`** is how the rest of your code refers to a URL. With `app_name = "tracker"` in `tracker/urls.py`, names are namespaced: `reverse("tracker:project_detail", kwargs={"slug": "apollo"})` returns `"/p/apollo/"`, and in templates `{% url 'tracker:project_detail' slug=project.slug %}` does the same. **Never hard-code paths**: URLs change, names don't.
- `Model.get_absolute_url()` is the convention for "the canonical URL of this object". The admin's "View on site" button, `redirect(obj)` and your templates all use it.

### Views: just functions

A view takes a request and returns a response. Shortcuts you'll use constantly:
- `render(request, template_name, context)`: render a template into an `HttpResponse`.
- `get_object_or_404(queryset_or_model, **lookup)`: `.get()` or raise `Http404`.
- `redirect(obj_or_url_name, **kwargs)`: a 302 to `obj.get_absolute_url()` or a reversed name.

### Authentication: who is asking

- `AuthenticationMiddleware` puts `request.user` on every request. It's either a real `User` or an `AnonymousUser` with `is_authenticated == False`.
- `@login_required` redirects anonymous users to `settings.LOGIN_URL` (default `/accounts/login/`) with `?next=<original path>`.
- `include("django.contrib.auth.urls")` gives you complete login, logout and password-change/reset views. You only supply templates.

Login works like this. `LoginView` checks the password with `authenticate()`, then `login()` writes the user's ID into the **session**: a server-side record keyed by a random ID stored in the `sessionid` cookie. Every later request loads the session and the user from it. Nothing about the user is in the cookie except that opaque key. Compare this with the JWTs you may have used in Node, which carry claims in the token itself. R1.03 adds token auth for API clients.

**Logout is POST-only** since Django 5.0. A GET to a logout URL can be triggered by any `<img src>` on any site, so it was removed. That's why the base template uses a small form with a CSRF token for "Log out".

### Authorization: scoping, and 404 vs 403

Being logged in isn't the same as being allowed. The rule for this app is: **you can only see projects you're a member of.** There are two ways to enforce it:

1. **Fetch, then check:** `project = get_object_or_404(Project, slug=slug)`, then `if not member: raise PermissionDenied` (a 403).
2. **Scope the query:** `get_object_or_404(Project.objects.filter(memberships__user=request.user), slug=slug)`. Non-members get a 404, exactly as if the project didn't exist.

Use **option 2**:
- **The default is safe.** Every lookup goes through a member-scoped queryset, so forgetting a check *fails closed* (404) instead of leaking data.
- **No existence leak.** A 403 tells an attacker "project `acquisition-target` exists". A 404 tells them nothing.

GitHub does exactly this for private repositories. You'll write the scoped queryset once as a helper and reuse it everywhere, including in DRF.

`memberships__user=request.user` follows the reverse FK from `Project` to `Membership`, then the `user` field. Double underscores walk relations in lookups. The membership pair is unique (D1.02), so this join can't duplicate projects. Keep that in mind: D2 shows joins that *can*.

### Templates

The Django template language is deliberately limited: no arbitrary Python, just variables, filters and tags. Logic belongs in views. Key behaviours:
- **Auto-escaping.** `{{ issue.title }}` HTML-escapes its value. An issue titled `<script>alert(1)</script>` renders as text. That's your XSS protection; never turn it off with `|safe` on user content.
- **Lookups.** `{{ issue.assignee.username }}` tries dict key, attribute, then list index. A missing value or `None` along the way renders as an empty string, *not* an error. Useful, and also a way to hide bugs.
- **Methods are called without arguments.** `{{ issue.get_status_display }}` calls the method. `{% for label in issue.labels.all %}` runs a query, which is why template loops cause N+1.
- **Inheritance.** `{% extends "base.html" %}` plus `{% block content %}` gives you one layout for all pages.
- **Where templates are found.** Every app's `templates/` folder (`APP_DIRS: True`) plus any folder in `DIRS`. The convention `tracker/templates/tracker/project_list.html`, referenced as `"tracker/project_list.html"`, namespaces templates by app so two apps' `detail.html` don't collide.

## Build

### 1. Settings

In `config/settings.py`:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],      # project-wide templates (base.html, registration/)
        "APP_DIRS": True,
        # OPTIONS unchanged
    },
]

LOGIN_REDIRECT_URL = "tracker:project_list"
LOGOUT_REDIRECT_URL = "login"
```

`LOGIN_REDIRECT_URL` accepts a URL *name*. It's where `LoginView` sends you when there's no `?next=`.

### 2. URLs

`config/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("tracker.urls")),
]
```

Create `tracker/urls.py`:

```python
from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("p/<slug:slug>/", views.project_detail, name="project_detail"),
    path("p/<slug:slug>/issues/<int:number>/", views.issue_detail, name="issue_detail"),
]
```

Why `/p/<slug>/` and not `/<slug>/`? A bare `/<slug>/` would capture `/accounts/` or `/admin/` if they came later in the list, and blocks future top-level pages. Give user-controlled path segments a prefix.

### 3. `get_absolute_url`

Add these to the models (and `from django.urls import reverse` at the top of `tracker/models.py`):

```python
# Project
    def get_absolute_url(self) -> str:
        return reverse("tracker:project_detail", kwargs={"slug": self.slug})

# Issue
    def get_absolute_url(self) -> str:
        return reverse(
            "tracker:issue_detail", kwargs={"slug": self.project.slug, "number": self.number}
        )
```

Note that `Issue.get_absolute_url` touches `self.project`. Called in a loop over issues whose project isn't already loaded, that's one query per issue: N+1. Keep it in mind for D2.

### 4. Views

`tracker/views.py`:

```python
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Issue, Project


def member_projects(request: HttpRequest) -> QuerySet[Project]:
    return Project.objects.filter(memberships__user=request.user)


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    return render(request, "tracker/project_list.html", {"projects": member_projects(request)})


@login_required
def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(member_projects(request), slug=slug)
    issues = project.issues.select_related("assignee")
    return render(request, "tracker/project_detail.html", {"project": project, "issues": issues})
```

`member_projects` is the single place that defines "projects this user may see". Everything goes through it.

`select_related("assignee")` makes the issue query JOIN the user table, because the template shows each assignee's username. Without it you get one extra query per issue. D2.02 explains it fully; use it now.

### 5. Templates

`templates/base.html` (project-level, next to `manage.py`):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}trackr{% endblock %}</title>
</head>
<body>
  <nav>
    <a href="{% url 'tracker:project_list' %}">Projects</a>
    {% if user.is_authenticated %}
      <span>Signed in as {{ user.username }}</span>
      <form method="post" action="{% url 'logout' %}" style="display:inline">
        {% csrf_token %}
        <button type="submit">Log out</button>
      </form>
    {% else %}
      <a href="{% url 'login' %}">Log in</a>
    {% endif %}
  </nav>
  <main>
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

`user` is available in every template because of the `auth` context processor in `TEMPLATES["OPTIONS"]`.

`templates/registration/login.html`. `LoginView` looks for exactly this path:

```html
{% extends "base.html" %}
{% block title %}Log in{% endblock %}
{% block content %}
  <h1>Log in</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_div }}
    <input type="hidden" name="next" value="{{ next }}">
    <button type="submit">Log in</button>
  </form>
{% endblock %}
```

`tracker/templates/tracker/project_list.html`:

```html
{% extends "base.html" %}
{% block title %}Projects{% endblock %}
{% block content %}
  <h1>Your projects</h1>
  <ul>
    {% for project in projects %}
      <li><a href="{{ project.get_absolute_url }}">{{ project.name }}</a></li>
    {% empty %}
      <li>You are not a member of any project yet.</li>
    {% endfor %}
  </ul>
{% endblock %}
```

`tracker/templates/tracker/project_detail.html`:

```html
{% extends "base.html" %}
{% block title %}{{ project.name }}{% endblock %}
{% block content %}
  <h1>{{ project.name }}</h1>
  <p>{{ project.description }}</p>
  <table>
    <thead><tr><th>#</th><th>Title</th><th>Status</th><th>Assignee</th></tr></thead>
    <tbody>
      {% for issue in issues %}
        <tr>
          <td>{{ issue.number }}</td>
          <td><a href="{{ issue.get_absolute_url }}">{{ issue.title }}</a></td>
          <td>{{ issue.get_status_display }}</td>
          <td>{{ issue.assignee.username|default:"—" }}</td>
        </tr>
      {% empty %}
        <tr><td colspan="4">No issues yet.</td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
```

`issue.get_absolute_url` reads `issue.project.slug` for every row. Is that N+1? **Not here.** Issues fetched through the reverse manager `project.issues` come back with `issue.project` already set to the `project` object you started from. Django calls these "known related objects". The same template fed `Issue.objects.filter(project=project)` *would* run one query per row, as the `get_absolute_url` step warned. You'll prove the difference with query counts in D2.02.

### 6. Your turn: `issue_detail`

Write the `issue_detail(request, slug, number)` view and its template `tracker/issue_detail.html`. Requirements:
- login required; non-members and nonexistent issues are both 404;
- **one** lookup that is already scoped to the user's projects, not "fetch then check";
- the page shows the issue's number, title, status (human label), priority (human label), reporter username, assignee username (or "unassigned"), the body with line breaks preserved, a link back to the project, and the comments with their authors;
- the issue page should take a fixed number of queries no matter how many comments there are.

<details><summary>Hint 1: the scoped lookup</summary>

Start from `Issue.objects` and filter through the relation chain `project → memberships → user`. Then add `project__slug=` and `number=` to the `get_object_or_404` call.
</details>

<details><summary>Hint 2: queries</summary>

The page touches `issue.project`, `issue.reporter` and `issue.assignee`: three FKs that `select_related` can JOIN in one go. Comments need their authors: `issue.comments.select_related("author")`.
</details>

<details><summary>Hint 3: line breaks</summary>

Look at the `linebreaks` filter in the built-in filter reference. Is it safe with user content? (Read what it does with escaping.)
</details>

### 7. Try it as two users

Create two users who share one project and each have a private one, via the admin or the shell. Log in as each in two different browsers (or one private window). Then try the other user's private project URL by hand.

## Checkpoint

```bash
uv run pytest ../checkpoints/d1/test_d1_04_views.py
```

## Pitfalls

- **`Project.objects.get(slug=slug)` in a view** raises `DoesNotExist`, a 500, for a bad URL. Use `get_object_or_404`.
- **Checking membership in the template** (`{% if user in project.members.all %}`). The data has already left the database, and the view returned 200. Scope in the query.
- **Forgetting `{% csrf_token %}` in a POST form.** You get a 403 "CSRF verification failed". D1.05 explains why that's the correct behaviour.
- **`{{ value|safe }}` on user input.** That's stored XSS.

## Explain it back

1. Trace `GET /p/apollo/issues/3/` through the URL resolver: which patterns are tried, in which `urlpatterns` lists, and what arguments does the view receive, with what types?
2. Why is a member-scoped queryset safer than fetch-then-check? Give the failure mode of each when a developer forgets something.
3. What exactly is in the `sessionid` cookie, and what isn't? What would it take to log out every session of a user?
4. Why must logout be a POST? Describe the attack against a GET logout.

## Read the source (optional)

`django/contrib/auth/decorators.py` (`login_required` is ~20 lines once you see `user_passes_test`) and `django/contrib/auth/__init__.py` (`login()` and `get_user()`), to see the session keys it writes.
