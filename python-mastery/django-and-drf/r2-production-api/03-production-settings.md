# R2.03 — Settings from the environment, and a clean `check --deploy`

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/r2/test_r2_03_production.py`

## What you'll have at the end

One `settings.py` that's safe in production and convenient in development, driven entirely by environment variables. Production mode:
- refuses to start without a real secret key;
- forces HTTPS-only cookies and HSTS;
- sends email over SMTP;
- passes `manage.py check --deploy --fail-level WARNING` with zero findings.

## Concepts

### Config in the environment

The *Twelve-Factor App* rule: code is the same in every environment; **configuration that differs between deploys comes from environment variables**. Secrets never live in the repo. Settings being plain Python (D1.01) makes this a few lines:

```python
DEBUG = env_bool("DJANGO_DEBUG", default=True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off")
    SECRET_KEY = "django-insecure-dev-only-key"
```

**About the default `DEBUG=True`.** It keeps `runserver` and `pytest` working with no setup. The cost: a production deploy that forgets `DJANGO_DEBUG=0` runs in debug mode. The opposite default (`False`, "fail closed") is stricter, and then every developer and CI job must set variables. Both are defensible. This guide picks convenience and adds two guards:
- in production mode, a missing `SECRET_KEY` crashes at startup;
- `check --deploy` runs in the deployment pipeline (and in the checkpoint).

Write down which default you'd choose for a team and why.

### What each production setting protects

| Setting | Attack it prevents |
|---|---|
| `DEBUG = False` | Debug pages show tracebacks, local variables, settings and SQL to anyone who triggers an error. With `DEBUG` on, Django also keeps every query in memory (`connection.queries`). |
| `SECRET_KEY` (long, random, secret) | Signs sessions, password-reset tokens, messages and `signing` payloads. Leaked means forgeable: anyone can mint a valid reset link. |
| `ALLOWED_HOSTS` | Host-header attacks, e.g. **password-reset poisoning**: an attacker requests a reset for your email with `Host: evil.com`, and the emailed link points to their server. |
| `SECURE_SSL_REDIRECT` | Plain-HTTP requests are redirected to HTTPS. |
| `SECURE_HSTS_SECONDS` (+ subdomains, preload) | Tells browsers "only ever use HTTPS for this domain", so an attacker on café Wi-Fi can't downgrade the first request. **Start with a small value** (e.g. 60 s) when first deploying. A year-long HSTS on a domain whose HTTPS later breaks locks users out until it expires. |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | Cookies are never sent over plain HTTP, where they could be sniffed. |
| `SECURE_PROXY_SSL_HEADER` | Behind a TLS-terminating proxy, Django sees plain HTTP. This tells it to trust `X-Forwarded-Proto: https`. **Only set it if your proxy strips that header from client requests.** Otherwise any client can claim HTTPS. |
| `CSRF_TRUSTED_ORIGINS` | Needed when the browser's `Origin` differs from the host Django sees, e.g. a separate SPA domain. Since Django 4.0 entries need the scheme: `https://app.example.com`. |

### Email in Django 6.1: `MAILERS`

Django 6.1 replaced the `EMAIL_BACKEND`/`EMAIL_HOST`/… settings with a `MAILERS` dict shaped like `DATABASES`. The old settings still work but are deprecated: Django's source flags them with `RemovedInDjango2028Warning`. The new shape is:

```python
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {"host": "...", "port": 587, "username": "...", "password": "...", "use_tls": True},
    },
}
```

`startproject` generates a console backend, which prints emails to the terminal and is right for development. `check --deploy` reports **`mail.E001`** for a development backend in production, as an *error* rather than a warning, because password-reset emails would silently go nowhere.

### Serving it

- **WSGI** (`config.wsgi:application`) runs under gunicorn, which is Linux/macOS only, or under waitress, which also works on Windows.
- **ASGI** (`config.asgi:application`) runs under uvicorn, hypercorn or granian. That's needed for async views, websockets and streaming.
- **`runserver` is never for production.** It's single-purpose, unhardened, and serves static files only in debug mode.
- **Static files**: `collectstatic` copies every app's static files to `STATIC_ROOT`, and something else serves them (nginx, a CDN, or `whitenoise` inside the Python process). With `DEBUG = False` the admin has no CSS until you set that up.
- **Database**: PostgreSQL in production. SQLite is a fine production database for single-server, low-write apps, but your concurrency lessons from D2.04 change with the engine. Set `CONN_MAX_AGE` to reuse connections, or use a pooler (Django ≥ 5.1 supports psycopg's pool via `OPTIONS["pool"]`).

## Build

### 1. Environment-driven core settings

Rewrite the top of `config/settings.py`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", default=True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off")
    SECRET_KEY = "django-insecure-dev-only-key"

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "testserver"]
```

`"testserver"` is the host Django's test client uses. Because the test runner always forces `DEBUG = False` (to match production), you might expect `ALLOWED_HOSTS` to bite in tests. It doesn't: the test runner also adds `testserver` itself. It's listed here for the shell and for scripts using `Client()` outside pytest.

### 2. Your turn: make `check --deploy` clean

Run:

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
DJANGO_ALLOWED_HOSTS=trackr.example.com \
uv run python manage.py check --deploy
```

For **each** finding: look up its ID in the [system check reference](https://docs.djangoproject.com/en/6.1/ref/checks/#security), explain the attack in `NOTES.md` in one sentence, and fix it **only for production mode** (inside `if not DEBUG:`). Development must keep working over plain HTTP. Include:
- SMTP `MAILERS` for production, configured from `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_USER` and `DJANGO_EMAIL_PASSWORD`. Read these with `os.environ.get(...)` and sensible defaults (`"localhost"`, `587`, `""`). Mail settings shouldn't stop the process from booting, and the checkpoint doesn't set them;
- `CSRF_TRUSTED_ORIGINS` from `DJANGO_CSRF_TRUSTED_ORIGINS`, comma-separated;
- `STATIC_ROOT = BASE_DIR / "staticfiles"`, so `collectstatic` has somewhere to go.

Done when this exits 0:

```bash
... uv run python manage.py check --deploy --fail-level WARNING
```

Re-run after each fix. The list can grow before it shrinks: setting `SECURE_HSTS_SECONDS` makes `security.W005` (subdomains) and `security.W021` (preload) appear, because those checks only make sense once HSTS is on. Each one is a decision; write down why you made it.

The drf-spectacular warnings from R2.02 show up in `check` too, as `drf_spectacular.W001`. If you skipped fixing them, this is where they come back.

### 3. Logging that's useful in production

Replace the temporary SQL logging from D2 with a permanent, environment-controlled config:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": os.environ.get("DJANGO_SQL_LOG_LEVEL", "INFO")},
    },
}
```

- Log to stdout and let the platform collect it (Twelve-Factor again).
- `DJANGO_SQL_LOG_LEVEL=DEBUG` turns SQL logging back on when you need it. Remember it only emits while `DEBUG = True`.
- `disable_existing_loggers: False` keeps loggers that were created before this config was applied. The default `True` silently mutes them.

### 4. A local `.env` and a production-like run

Create `trackr/.env`. It's already in `.gitignore`; verify that.

```
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<paste a long random value>
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

and run under a real ASGI server (`uvicorn` isn't a project dependency, so `--with` adds it for this one command):

```bash
uv run --env-file .env python manage.py collectstatic --noinput
uv run --env-file .env --with uvicorn uvicorn config.asgi:application --port 8001
```

Open http://127.0.0.1:8001/api/projects/. It redirects to HTTPS (`SECURE_SSL_REDIRECT`) and fails, because uvicorn here speaks plain HTTP. That's correct behaviour: in production a TLS proxy sits in front. Answer in `NOTES.md`: which setting makes Django trust that proxy, and what goes wrong if the proxy doesn't strip the header?

## Checkpoint

```bash
uv run pytest ../checkpoints/r2/test_r2_03_production.py
uv run pytest ../checkpoints              # everything, D1 through R2
uv run ruff check .
```

The checkpoint runs `manage.py` in a subprocess with a clean environment, which is the closest a test gets to a real deploy.

## Pitfalls

- **Secrets in `settings.py`** or committed `.env` files.
- **Year-long HSTS on the first deploy.**
- **`SECURE_PROXY_SSL_HEADER` without a proxy that strips it.**
- **`ALLOWED_HOSTS = ["*"]`** "to make the error go away". That reopens host-header attacks.
- **Console or locmem email in production.** Django 6.1's `mail.E001` exists because of this.
- **Running `runserver` in production.**

## Explain it back

1. Describe password-reset poisoning step by step, and which setting stops it.
2. Why is HSTS dangerous to roll out with a long max-age immediately?
3. What can an attacker do with your `SECRET_KEY`? Name two concrete forgeries.
4. **Stage 2 retrospective** (one page in `NOTES.md`): the three most important things you learned about Django and DRF. One thing you'd do differently if you started trackr again. One question about how Django works internally that you want Stage 3 to answer. Tier 0.1 and Tier 1 probably will.

## Stretch: types

`uv add --dev django-stubs[compatible-mypy] djangorestframework-stubs[compatible-mypy]`, configure the mypy plugin (`[tool.mypy] plugins = ["mypy_django_plugin.main"]` and `[tool.django-stubs] django_settings_module = "config.settings"`), and get `uv run mypy trackr` passing. You'll then want to write `serializers.ModelSerializer[Project]`. The stubs make that legal for mypy, but at runtime DRF's classes aren't subscriptable: `TypeError: type 'ModelSerializer' is not subscriptable`. `django-stubs-ext` patches `__class_getitem__` in for you. Call `django_stubs_ext.monkeypatch(extra_classes=[serializers.ModelSerializer, viewsets.ModelViewSet])` at the top of settings; Django's own classes are covered without `extra_classes`. Knowing why a type-checker-only construct needs a runtime patch is a Stage 3 Tier 0.2 topic.
