# D1.05 — Forms, POST/redirect/GET, CSRF, and never trusting submitted choices

**Time:** ~2 h · **Checkpoint:** `uv run pytest ../checkpoints/d1/test_d1_05_forms.py`

## What you'll have at the end

A "New issue" page that:
- validates input and re-renders with errors;
- assigns the next issue number;
- redirects to the new issue;
- refuses assignees who aren't project members, even when someone crafts the POST by hand.

## Concepts

### What a Django form does

A form is a **boundary object**. It turns untrusted strings from `request.POST` into validated Python values, and back into HTML. Its life:

1. `form = IssueForm(request.POST)` **binds** the raw data. Nothing is validated yet.
2. `form.is_valid()` runs `full_clean()`:
   - for each field, `field.clean(raw)` converts the value (`"3"` → `3`) and runs the field's validators;
   - then `clean_<fieldname>()` methods you define;
   - then `clean()` for cross-field rules.
   
   Errors collect in `form.errors`; good values in `form.cleaned_data`.
3. Invalid: re-render the same template with the bound form. It remembers what the user typed and shows errors next to fields.
4. Valid: use `form.cleaned_data`, or `form.save()` for a ModelForm.

A **`ModelForm`** derives its fields from a model: `CharField(max_length=200)` becomes a form field with the same max length, choices become a `<select>`, and a `ForeignKey` becomes a `ModelChoiceField` whose allowed values are a **queryset**. That last point matters below.

If this looks like Pydantic models in FastAPI, it is the same job. R1's serializers are the same job again, with JSON instead of HTML.

### The POST/redirect/GET pattern

After a successful POST, **redirect** (302) instead of rendering a page. If you render, the browser's current page is the result of a POST, and Refresh re-submits it, creating a duplicate issue. Redirecting makes the browser GET the new issue's URL, which is safe to refresh. Invalid POSTs *do* render directly (status 200 with errors), because nothing was written.

### CSRF: why the token exists

Your session cookie is sent with *every* request to your domain, including requests triggered by *other* sites. A malicious page can contain:

```html
<form action="https://trackr.example.com/p/apollo/issues/new/" method="post">…</form>
<script>document.forms[0].submit()</script>
```

Your browser would send the POST *with your session cookie*, and the issue gets filed as you. **Cross-Site Request Forgery.**

Django's defence works like this:
- `CsrfViewMiddleware` requires every unsafe-method request (POST, PUT, PATCH, DELETE) to carry a token that matches a secret in the `csrftoken` cookie;
- `{% csrf_token %}` embeds that token in your forms;
- the attacker's page can't read your cookie or your page, so it can't produce the token.

Modern browsers' `SameSite=Lax` cookie default blocks most of these attacks too. CSRF tokens are still the defence that doesn't depend on browser behaviour.

The test client skips CSRF checks by default, which is convenient for testing views. The checkpoint includes one test with `Client(enforce_csrf_checks=True)` to prove the protection is on.

### Never trust submitted choices

The assignee `<select>` only *displays* project members. But a POST is just text, and anyone can send `assignee=17` for any user ID in the system. If the form's `ModelChoiceField` queryset is `User.objects.all()` (the ModelForm default), that validates, and you've let a user link a stranger to their issue. Worse, in many apps the same bug leaks data: think "share with user ID N".

**The fix is server-side: restrict the field's queryset**, and validation rejects anything outside it. This is the same idea as scoping querysets in D1.04, applied to *inputs*. You'll do it again in DRF (R1.04), where it matters even more because there's no HTML form to hide behind.

### Issue numbers, naively

The next number is `max(existing numbers in this project) + 1`. Now think about two requests arriving at the same moment:
- both read max = 4;
- both try to insert #5;
- the unique constraint from D1.02 rejects the second one, which becomes an `IntegrityError` and a 500.

So the constraint stops corrupt data, but the user still sees an error. That's a **race condition**. For now, accept it knowingly. D2.04 fixes it with a transaction and a row lock, and you'll understand why both are needed.

## Build

### 1. `tracker/forms.py`

```python
from typing import Any

from django import forms

from .models import Issue, Project


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["title", "body", "priority", "assignee"]

    def __init__(self, *args: Any, project: Project, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = project.members.all()
```

- **`fields` is an allow-list.** Never use `fields = "__all__"` on a form that faces users: the day someone adds an `is_approved` field to the model, it silently becomes user-editable. (This is called *mass assignment*.) `project`, `number`, `reporter` and `status` are *not* in the list because the server decides them.
- **`project` is a required keyword-only argument.** The form can't be built without knowing which project's members are valid, and `*` in the signature makes forgetting it a `TypeError` instead of a silent security hole.

### 2. The view

Add to `tracker/views.py`:

```python
from django.shortcuts import get_object_or_404, redirect, render

from .forms import IssueForm


@login_required
def issue_create(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(member_projects(request), slug=slug)
    if request.method == "POST":
        form = IssueForm(request.POST, project=project)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.project = project
            issue.reporter = request.user
            last = project.issues.order_by("-number").first()
            issue.number = (last.number + 1) if last else 1
            issue.save()
            return redirect(issue)
    else:
        form = IssueForm(project=project)
    return render(request, "tracker/issue_form.html", {"form": form, "project": project})
```

- **`form.save(commit=False)`** builds the `Issue` instance from `cleaned_data` without saving it, so you can set the server-owned fields first.
  - The catch: many-to-many fields can't be saved before the row exists. With `commit=False`, Django gives the form a `save_m2m()` method that you must call after `issue.save()`. There are no M2M fields here yet. D2.04 replaces all of this with a service and avoids the trap.
- **`redirect(issue)`** calls `issue.get_absolute_url()`.
- **Membership is checked first.** `project` comes from `member_projects`, so non-members get a 404 before any form handling.
- **The race described above is right here**, between `.first()` and `.save()`.

URL, in `tracker/urls.py` **before** the issue-detail pattern:

```python
    path("p/<slug:slug>/issues/new/", views.issue_create, name="issue_create"),
```

Order doesn't strictly matter here, because `<int:number>` can't match `new`. If the detail route used `<str:...>`, it would swallow `new`. Put fixed paths before parameterised siblings out of habit.

### 3. Template: `tracker/templates/tracker/issue_form.html`

```html
{% extends "base.html" %}
{% block title %}{% if form.instance.pk %}Edit issue{% else %}New issue{% endif %}{% endblock %}
{% block content %}
  <h1>{% if form.instance.pk %}Edit #{{ form.instance.number }}{% else %}New issue in {{ project.name }}{% endif %}</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_div }}
    <button type="submit">Save</button>
  </form>
{% endblock %}
```

It's written for both create and edit (D1.06 reuses it): a ModelForm's `instance.pk` is `None` until the object exists.

Add a "New issue" link on the project page:

```html
<p><a href="{% url 'tracker:issue_create' slug=project.slug %}">New issue</a></p>
```

### 4. Try to break it

1. Submit an empty title. You should get errors and nothing created.
2. In the browser devtools, edit the assignee `<option value="…">` to another user's ID who isn't in the project and submit. The form should reject it.
3. Remove `{% csrf_token %}` from the template and submit. You get a 403. Put it back.
4. Submit, then press Refresh on the issue page. No duplicate is created.

## Checkpoint

```bash
uv run pytest ../checkpoints/d1/test_d1_05_forms.py
```

## Pitfalls

- **`fields = "__all__"`** (mass assignment).
- **Rendering after a successful POST** (duplicate submissions).
- **Filtering choices only in the template or with JavaScript.** Only the queryset is enforced.
- **`@csrf_exempt` to make an error go away.** If a legitimate client can't send the token, the client is the bug.
- **`form.save(commit=False)` with M2M fields and no `save_m2m()`.** The M2M values are silently dropped.

## Explain it back

1. Walk through `is_valid()` for a POST with `priority="9"`: which method rejects it, and where does the message end up?
2. Explain CSRF to a TypeScript colleague who only builds SPAs with bearer tokens. Why don't bearer-token APIs need CSRF tokens? (R1.03 relies on this.)
3. Describe the numbering race step by step with two concurrent requests. What does the unique constraint guarantee, and what does it not?
4. Why is `project` a keyword-only constructor argument on the form?
