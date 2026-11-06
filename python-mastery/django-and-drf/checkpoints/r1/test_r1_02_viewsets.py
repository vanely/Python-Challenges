"""R1.02 — ViewSets, routers, and lookup by slug."""

import pytest
from django.urls import resolve, reverse
from rest_framework.viewsets import ModelViewSet

pytestmark = pytest.mark.django_db


def test_router_urls() -> None:
    assert reverse("project-list") == "/api/projects/"
    assert reverse("project-detail", kwargs={"slug": "apollo"}) == "/api/projects/apollo/"
    assert issubclass(resolve("/api/projects/").func.cls, ModelViewSet)


def test_retrieve_update_by_slug(api_client, make_project) -> None:
    project = make_project(slug="apollo", name="Apollo")
    api_client.force_authenticate(project.owner)
    url = reverse("project-detail", kwargs={"slug": "apollo"})

    assert api_client.get(url).data["name"] == "Apollo"
    response = api_client.patch(url, {"description": "to the moon"}, format="json")
    assert response.status_code == 200
    project.refresh_from_db()
    assert project.description == "to the moon"


def test_non_members_get_404(api_client, make_user, make_project) -> None:
    make_project(slug="apollo")
    api_client.force_authenticate(make_user())
    assert api_client.get(reverse("project-detail", kwargs={"slug": "apollo"})).status_code == 404


def test_list_is_paginated(api_client, make_user, make_project) -> None:
    me = make_user()
    for _ in range(3):
        make_project(owner=me)
    api_client.force_authenticate(me)
    data = api_client.get(reverse("project-list")).data
    assert data["count"] == 3
    assert len(data["results"]) == 3
