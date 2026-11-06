# D1 — Django core: a server-rendered issue tracker

By the end of D1, `trackr` is a working multi-user issue tracker in the browser:
- users log in;
- see only the projects they belong to;
- open a project to see its issues;
- file new issues through a validated form;
- edit them;
- staff manage everything through the admin.

No JavaScript. No API yet; that's R1.

## Why server-rendered first

You'll mostly build APIs with Django in practice, so why start with templates? Because the classic stack exercises every layer Django has: URL routing, views, the ORM, forms, auth, sessions, CSRF, middleware and templates. DRF is built *on* those layers: a DRF serializer is a form with a different output format, and a DRF permission is a view mixin. Learning them in plain Django first makes R1 a short step instead of a new world.

## Steps

| Step | File | You build | Checkpoint |
|---|---|---|---|
| 1 | [01-setup.md](01-setup.md) | Project skeleton, custom user model, first migration | `test_d1_01_setup.py` |
| 2 | [02-models.md](02-models.md) | `Project`, `Membership`, `Issue`, `Comment` with constraints | `test_d1_02_models.py` |
| 3 | [03-admin.md](03-admin.md) | An admin your support team could actually use | `test_d1_03_admin.py` |
| 4 | [04-views-urls-templates.md](04-views-urls-templates.md) | Login, project list/detail, issue detail, scoped to the user | `test_d1_04_views.py` |
| 5 | [05-forms.md](05-forms.md) | Create-issue form, POST/redirect/GET, CSRF, server-side choice validation | `test_d1_05_forms.py` |
| 6 | [06-class-based-views.md](06-class-based-views.md) | List/detail as CBVs, an edit view | `test_d1_06_cbv.py` |

## The domain

```
User ──< Membership >── Project ──< Issue ──< Comment
            (role)                 (number, status, priority,
                                    reporter, assignee)
```

- A **Project** has members through **Membership**, which carries a role (`admin` or `member`).
- An **Issue** belongs to one project. It has a per-project number (#1, #2, … like GitHub), a status, a priority, a reporter and an optional assignee.
- **Comments** belong to issues.

D2 adds **Labels**.

## Done means

- `uv run pytest ../checkpoints/d1` is green.
- `uv run ruff check .` is clean.
- You've clicked through the whole app in a browser as two different users.
- `NOTES.md` has answers to every "Explain it back" question from D1, plus a short retrospective: what surprised you coming from TypeScript and FastAPI, and what Django did for you that you'd have hand-written in Express.
