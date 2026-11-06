"""D1.05 — forms, POST/redirect/GET, CSRF, and never trusting submitted choices."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(client, make_user, make_project):
    member = make_user("member")
    project = make_project(slug="apollo", members=(member,))
    client.force_login(member)
    return client, project, member


def test_form_page_renders_with_csrf_token(setup) -> None:
    client, project, _ = setup
    response = client.get(reverse("tracker:issue_create", kwargs={"slug": "apollo"}))
    assert response.status_code == 200
    assert b"csrfmiddlewaretoken" in response.content


def test_valid_post_creates_numbered_issue_and_redirects(setup) -> None:
    from tracker.models import Issue

    client, project, member = setup
    url = reverse("tracker:issue_create", kwargs={"slug": "apollo"})
    r1 = client.post(url, {"title": "First", "body": "", "priority": 2})
    r2 = client.post(url, {"title": "Second", "body": "", "priority": 3, "assignee": member.pk})

    assert r1.status_code == 302 and r1["Location"] == "/p/apollo/issues/1/"
    assert r2.status_code == 302 and r2["Location"] == "/p/apollo/issues/2/"
    second = Issue.objects.get(project=project, number=2)
    assert second.reporter == member
    assert second.assignee == member
    assert second.priority == 3


def test_invalid_post_rerenders_with_errors(setup) -> None:
    from tracker.models import Issue

    client, _, _ = setup
    response = client.post(
        reverse("tracker:issue_create", kwargs={"slug": "apollo"}), {"title": "", "priority": 2}
    )
    assert response.status_code == 200
    assert response.context["form"].errors["title"]
    assert not Issue.objects.exists()


def test_cannot_assign_someone_outside_the_project(setup, make_user) -> None:
    from tracker.models import Issue

    client, _, _ = setup
    outsider = make_user("outsider")
    response = client.post(
        reverse("tracker:issue_create", kwargs={"slug": "apollo"}),
        {"title": "Sneaky", "priority": 2, "assignee": outsider.pk},
    )
    assert response.status_code == 200
    assert "assignee" in response.context["form"].errors
    assert not Issue.objects.exists()


def test_non_member_cannot_post(client, make_user, make_project) -> None:
    make_project(slug="apollo")
    client.force_login(make_user())
    response = client.post(
        reverse("tracker:issue_create", kwargs={"slug": "apollo"}), {"title": "x", "priority": 2}
    )
    assert response.status_code == 404


def test_csrf_is_enforced(make_user, make_project) -> None:
    from django.test import Client

    member = make_user()
    make_project(slug="apollo", members=(member,))
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(member)
    response = strict.post(
        reverse("tracker:issue_create", kwargs={"slug": "apollo"}), {"title": "x", "priority": 2}
    )
    assert response.status_code == 403
