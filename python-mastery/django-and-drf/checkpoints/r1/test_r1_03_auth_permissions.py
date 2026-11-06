"""R1.03 — authentication (who are you?) vs permissions (may you?)."""

import pytest
from django.urls import reverse

PASSWORD = "correct-horse-battery-staple"  # matches make_user in checkpoints/conftest.py

pytestmark = pytest.mark.django_db


def test_anonymous_gets_401_with_a_challenge(api_client) -> None:
    response = api_client.get(reverse("project-list"))
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Token")


def test_token_flow(api_client, make_user, make_project) -> None:
    user = make_user("ada")
    make_project(owner=user, slug="apollo")

    response = api_client.post(
        reverse("api-token"), {"username": "ada", "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    token = response.data["token"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert api_client.get(reverse("project-list")).status_code == 200

    api_client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
    assert api_client.get(reverse("project-list")).status_code == 401


def test_wrong_password_does_not_issue_a_token(api_client, make_user) -> None:
    make_user("ada")
    response = api_client.post(
        reverse("api-token"), {"username": "ada", "password": "nope"}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("who", "method", "expected"),
    [
        ("admin", "get", 200),
        ("admin", "patch", 200),
        ("admin", "delete", 204),
        ("member", "get", 200),
        ("member", "patch", 403),
        ("member", "delete", 403),
        ("outsider", "get", 404),
        ("outsider", "patch", 404),
        ("outsider", "delete", 404),
    ],
)
def test_permission_matrix(api_client, make_user, make_project, who, method, expected) -> None:
    admin, member, outsider = make_user(), make_user(), make_user()
    make_project(owner=admin, members=(member,), slug="apollo")
    api_client.force_authenticate({"admin": admin, "member": member, "outsider": outsider}[who])

    url = reverse("project-detail", kwargs={"slug": "apollo"})
    kwargs = {"data": {"name": "Renamed"}, "format": "json"} if method == "patch" else {}
    response = getattr(api_client, method)(url, **kwargs)
    assert response.status_code == expected
