"""R2.03 — settings from the environment, and a clean `check --deploy`."""

import os
import secrets
import subprocess
import sys

from django.conf import settings


def run_manage(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=settings.BASE_DIR,
        env={**clean, "DJANGO_SETTINGS_MODULE": "config.settings", **env},
        capture_output=True,
        text=True,
        timeout=60,
    )


PROD_ENV = {
    "DJANGO_DEBUG": "0",
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
    "DJANGO_ALLOWED_HOSTS": "trackr.example.com",
}


def test_deploy_check_passes_in_production_mode() -> None:
    result = run_manage("check", "--deploy", "--fail-level", "WARNING", **PROD_ENV)
    assert result.returncode == 0, result.stdout + result.stderr


def test_production_refuses_to_start_without_a_secret_key() -> None:
    env = {k: v for k, v in PROD_ENV.items() if k != "DJANGO_SECRET_KEY"}
    result = run_manage("check", **env)
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_debug_is_read_from_the_environment() -> None:
    result = run_manage(
        "shell", "-c", "from django.conf import settings; print(settings.DEBUG)", **PROD_ENV
    )
    assert result.stdout.strip().endswith("False"), result.stderr
