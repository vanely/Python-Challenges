# D1.01 — Project skeleton, custom user model, the first request

**Time:** ~1.5 h · **Checkpoint:** `uv run pytest ../checkpoints/d1/test_d1_01_setup.py`

## What you'll have at the end

A Django project named `config` inside a folder named `trackr/`, with two apps (`accounts`, `tracker`) and a custom `User` model. The database is migrated and the admin login page loads.

## Concepts

### Project vs app

Django splits code into one **project** and many **apps**.

- The **project** (`config/` here) holds settings, the root URL configuration, and the WSGI/ASGI entry points. It is wiring, not features.
- An **app** is a Python package that owns one slice of the domain: its models, views, URLs, templates, admin and migrations. Apps are listed in `INSTALLED_APPS`. That list is how Django finds their models, migrations, templates and admin modules.

Naming the project `config` instead of `trackr` is a common convention. It makes `config/settings.py` obviously the settings and avoids a `trackr/trackr/` folder.

### What happens on a request

Read this once now and again after D1.04. Everything later is a detail of one of these stages.

1. **Server → WSGI/ASGI.** A server (the dev server, gunicorn or uvicorn in production) receives HTTP and calls `config.wsgi.application` (or `asgi`) with the request environment.
2. **`HttpRequest`.** Django's handler builds a request object: method, path, headers, `GET`/`POST` dicts, cookies.
3. **Middleware, inbound.** Each class in `MIDDLEWARE` runs top to bottom. `SessionMiddleware` loads the session from the cookie. `AuthenticationMiddleware` attaches `request.user` (lazily). `CsrfViewMiddleware` checks the CSRF token on unsafe methods.
4. **URL resolution.** `ROOT_URLCONF` is tried pattern by pattern. The first match picks a view and extracts arguments from the path. No match → 404.
5. **The view.** A callable `view(request, **kwargs) -> HttpResponse`. That signature is the whole contract; everything else is convenience.
6. **Middleware, outbound.** Middleware runs bottom to top on the response (adding headers, saving the session).
7. **Back to the server**, which writes the bytes.

An onion: middleware wraps the view. If you've used Express or Koa, it's the same model with a fixed, settings-declared order.

### Settings

`config/settings.py` is a plain Python module. Django imports it once at startup, at whatever path `DJANGO_SETTINGS_MODULE` names (`manage.py` sets it to `config.settings`). Anything in it is readable through `django.conf.settings`. Two consequences:
- settings are global and read at import time;
- you can compute them with ordinary Python.

R2.03 uses the second fact to read them from environment variables.

### Why a custom user model on day one

Django ships `django.contrib.auth.models.User`. **Don't use it directly.** Set `AUTH_USER_MODEL` to your own model before the first `migrate`, even if the model is empty:

```python
class User(AbstractUser):
    pass
```

The user table is referenced by foreign keys from every app, including Django's own `admin` and `auth` migrations. Swapping it after the first migration means rewriting migration history across apps, and the Django docs call it out as a painful manual job. With your own model from the start, adding a field later (`timezone`, `avatar`) is an ordinary migration. It costs nothing now and saves a lot later.

Code that refers to the user model must not import `accounts.models.User` directly when it can avoid it:
- **in models**, use the string `settings.AUTH_USER_MODEL` for foreign keys;
- **at runtime**, use `django.contrib.auth.get_user_model()`.

That way reusable code keeps working with whatever model the project chose.

### Migrations, in one paragraph

Models are Python classes; the database has tables. **Migrations** are versioned Python files that describe schema changes as operations (`CreateModel`, `AddField`, …).
- `makemigrations` diffs your models against the state the existing migrations produce, and writes a new migration.
- `migrate` applies unapplied migrations and records them in the `django_migrations` table.

Migrations are code. Commit them, review them, and never edit one that has been applied somewhere you don't control. D2.04 covers data migrations.

## Build

### 1. Create the project

From `python-mastery/django-and-drf/` (where `pyproject.toml` is):

```bash
uv sync
uv run django-admin startproject config trackr
cd trackr
uv run python manage.py startapp accounts
uv run python manage.py startapp tracker
```

`startproject config trackr` means "create a project package named `config` inside a directory named `trackr`". You now have:

```
trackr/
  manage.py            # CLI entry point; sets DJANGO_SETTINGS_MODULE=config.settings
  config/
    settings.py  urls.py  wsgi.py  asgi.py
  accounts/            # app: models.py, admin.py, apps.py, views.py, migrations/
  tracker/
```

Delete `accounts/tests.py`, `tracker/tests.py` and `accounts/views.py`. The checkpoints and your own tests live elsewhere, and `accounts` has no views yet.

### 2. The custom user model

`accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass
```

`AbstractUser` gives you `username`, `email`, `first_name`, `last_name`, password hashing, `is_staff`, `is_active`, `is_superuser`, groups and permissions. Since it's abstract (`Meta.abstract = True`), it has no table of its own. Your subclass gets the table `accounts_user`.

`accounts/admin.py`. Register it with Django's `UserAdmin`, which knows how to handle password fields:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

admin.site.register(User, UserAdmin)
```

### 3. Settings

In `config/settings.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "tracker",
]

AUTH_USER_MODEL = "accounts.User"
```

The format is `"<app_label>.<ModelName>"`, not a Python import path.

Read the rest of the generated `settings.py` top to bottom and look up any setting you can't explain in [the settings reference](https://docs.djangoproject.com/en/6.1/ref/settings/). Note `SECRET_KEY` and `DEBUG = True`: both are fine for local development and dangerous in production. R2.03 fixes them.

### 4. Migrate and run

```bash
uv run python manage.py makemigrations accounts
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/admin/ and log in. Open http://127.0.0.1:8000/ and you get Django's "The install worked successfully!" page. That page only shows while `DEBUG` is on and you have no URL patterns of your own.

Look at what `makemigrations` produced: `accounts/migrations/0001_initial.py`. Then see the SQL it maps to:

```bash
uv run python manage.py sqlmigrate accounts 0001
```

## Checkpoint

```bash
uv run pytest ../checkpoints/d1/test_d1_01_setup.py
```

The tests check that:
- the user model is yours;
- both apps are installed;
- users land in `accounts_user`;
- the admin login renders.

## Pitfalls

- **Running `migrate` before setting `AUTH_USER_MODEL`.** If you did, delete `db.sqlite3` and run it again. In a real project with data, that's the expensive mistake described above.
- **`startproject trackr` without `config`** gives `trackr/trackr/settings.py`. The checkpoints assume `config`.
- **Importing `User` from `django.contrib.auth.models`** anywhere in your code. That's the built-in model you're *not* using.

## Explain it back (in `NOTES.md`)

1. List the seven stages of a request in your own words. Where does `request.user` come from, and at which stage?
2. Why must `AUTH_USER_MODEL` be set before the first `migrate`? Which existing migrations would reference the user table?
3. What's the difference between `makemigrations` and `migrate`? Which one talks to the database?
4. `AbstractUser` has `class Meta: abstract = True`. What does that change about tables and inheritance? Contrast it with multi-table inheritance, which you get by subclassing a concrete model.

## Read the source (optional, 20 min)

`django/core/handlers/base.py`, method `BaseHandler.load_middleware`. It builds the onion from `MIDDLEWARE` *in reverse*, wrapping each handler in the next middleware. Ten minutes here makes the request diagram concrete.
