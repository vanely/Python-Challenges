"""R1.01 — serializers translate and validate; the first endpoint."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_project_serializer_output_shape(make_user, make_project) -> None:
    from api.serializers import ProjectSerializer

    project = make_project(owner=make_user("ada"), name="Apollo", slug="apollo")
    data = ProjectSerializer(project).data
    assert data["slug"] == "apollo"
    assert data["name"] == "Apollo"
    assert data["owner"] == "ada", "represent the owner by username, not by primary key"
    assert "id" not in data and "pk" not in data
    assert "next_issue_number" not in data, "don't leak internals"


@pytest.mark.parametrize(
    ("payload", "bad_field"),
    [
        ({"slug": "apollo"}, "name"),
        ({"name": "Apollo", "slug": "Not A Slug!"}, "slug"),
        ({"name": "Apollo", "slug": "api"}, "slug"),
        ({"name": "x" * 101, "slug": "long"}, "name"),
    ],
)
def test_project_serializer_validation(payload, bad_field) -> None:
    from api.serializers import ProjectSerializer

    serializer = ProjectSerializer(data=payload)
    assert not serializer.is_valid()
    assert bad_field in serializer.errors


def test_owner_cannot_be_set_by_the_client(api_client, make_user) -> None:
    me = make_user("me")
    make_user("someone")
    api_client.force_authenticate(me)
    response = api_client.post(
        reverse("project-list"),
        {"name": "Apollo", "slug": "apollo", "owner": "someone"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["owner"] == "me"


def test_list_and_create(api_client, make_user, make_project) -> None:
    from tracker.models import Membership, Project

    me = make_user()
    make_project(owner=me, slug="mine")
    make_project(slug="not-mine")
    api_client.force_authenticate(me)

    listing = api_client.get(reverse("project-list"))
    assert listing.status_code == 200
    rows = listing.data["results"] if isinstance(listing.data, dict) else listing.data
    assert [p["slug"] for p in rows] == ["mine"]

    created = api_client.post(
        reverse("project-list"), {"name": "New", "slug": "new-one"}, format="json"
    )
    assert created.status_code == 201
    project = Project.objects.get(slug="new-one")
    assert project.owner == me
    assert project.memberships.get(user=me).role == Membership.Role.ADMIN
