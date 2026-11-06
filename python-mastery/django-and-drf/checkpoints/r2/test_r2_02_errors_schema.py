"""R2.02 — one error shape, throttling, and an OpenAPI schema that validates."""

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_not_found_uses_the_envelope(api_client, make_user) -> None:
    api_client.force_authenticate(make_user())
    response = api_client.get(reverse("project-detail", kwargs={"slug": "nope"}))
    assert response.status_code == 404
    error = response.data["error"]
    assert error["code"] == "not_found"
    assert error["message"]
    assert error["details"] is None


def test_validation_errors_use_the_envelope(api_client, make_user) -> None:
    api_client.force_authenticate(make_user())
    response = api_client.post(reverse("project-list"), {"slug": "Bad Slug"}, format="json")
    assert response.status_code == 400
    error = response.data["error"]
    assert error["code"] == "invalid"
    assert set(error["details"]) >= {"name", "slug"}


def test_auth_errors_use_the_envelope(api_client) -> None:
    response = api_client.get(reverse("project-list"))
    assert response.status_code == 401
    assert response.data["error"]["code"] == "not_authenticated"


def test_token_endpoint_is_throttled(api_client, make_user) -> None:
    cache.clear()
    make_user("ada")
    responses = [
        api_client.post(reverse("api-token"), {"username": "ada", "password": "wrong"}, format="json")
        for _ in range(6)
    ]
    cache.clear()
    assert [r.status_code for r in responses[:5]] == [400] * 5
    throttled = responses[5]
    assert throttled.status_code == 429
    assert "Retry-After" in throttled
    assert throttled.data["error"]["code"] == "throttled"


def test_schema_endpoint(api_client) -> None:
    response = api_client.get(reverse("schema"), {"format": "json"})
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/projects/" in paths
    assert "/api/projects/{project_slug}/issues/{number}/close/" in paths


def test_schema_validates_without_warnings(tmp_path) -> None:
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "s.yml"))
