"""D1.01 — project skeleton, custom user model, and the first request."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser


def test_custom_user_model_is_configured() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    User = get_user_model()
    assert User._meta.app_label == "accounts"
    assert issubclass(User, AbstractUser)


def test_both_apps_are_installed() -> None:
    assert "accounts" in settings.INSTALLED_APPS
    assert "tracker" in settings.INSTALLED_APPS


@pytest.mark.django_db
def test_users_table_is_yours(django_user_model) -> None:
    user = django_user_model.objects.create_user(username="ada", password="x" * 12)
    assert user._meta.db_table == "accounts_user"
    assert user.check_password("x" * 12)


@pytest.mark.django_db
def test_admin_login_page_renders(client) -> None:
    response = client.get("/admin/login/")
    assert response.status_code == 200
