"""R1.04 — a nested resource, scoped relations, and state changes as actions."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx(api_client, make_user, make_project):
    from tracker.models import Label

    me, teammate = make_user("me"), make_user("teammate")
    project = make_project(owner=me, members=(teammate,), slug="apollo")
    Label.objects.create(project=project, name="bug")
    api_client.force_authenticate(me)
    return api_client, project, me, teammate


def field_errors(response) -> dict:
    """Works before and after R2.02 wraps errors in an envelope."""
    data = response.data
    return data["error"]["details"] if "error" in data else data


def issues_url(slug: str = "apollo") -> str:
    return reverse("project-issue-list", kwargs={"project_slug": slug})


def issue_url(number: int, slug: str = "apollo") -> str:
    return reverse("project-issue-detail", kwargs={"project_slug": slug, "number": number})


def test_urls() -> None:
    assert issues_url() == "/api/projects/apollo/issues/"
    assert issue_url(3) == "/api/projects/apollo/issues/3/"


def test_create_assigns_number_and_reporter(ctx) -> None:
    client, project, me, teammate = ctx
    payload = {"title": "Crash", "assignee": "teammate", "labels": ["bug"], "priority": 3}
    r1 = client.post(issues_url(), payload, format="json")
    r2 = client.post(issues_url(), {"title": "Second"}, format="json")

    assert r1.status_code == 201, r1.data
    assert r1.data["number"] == 1 and r2.data["number"] == 2
    assert r1.data["reporter"] == "me"
    assert r1.data["assignee"] == "teammate"
    assert r1.data["labels"] == ["bug"]


def test_client_cannot_set_server_owned_fields(ctx) -> None:
    client, *_ = ctx
    response = client.post(
        issues_url(),
        {"title": "x", "number": 99, "status": "closed", "reporter": "teammate"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["number"] == 1
    assert response.data["status"] == "open"
    assert response.data["reporter"] == "me"


def test_relations_are_scoped_to_the_project(ctx, make_user, make_project) -> None:
    from tracker.models import Label

    client, *_ = ctx
    make_user("outsider")
    Label.objects.create(project=make_project(), name="foreign")

    r = client.post(issues_url(), {"title": "x", "assignee": "outsider"}, format="json")
    assert r.status_code == 400 and "assignee" in field_errors(r)
    r = client.post(issues_url(), {"title": "x", "labels": ["foreign"]}, format="json")
    assert r.status_code == 400 and "labels" in field_errors(r)


def test_list_retrieve_patch(ctx, make_issue) -> None:
    client, project, *_ = ctx
    make_issue(project, title="one")
    make_issue(project, title="two")

    listing = client.get(issues_url()).data
    assert [i["number"] for i in listing["results"]] == [2, 1]
    assert client.get(issue_url(1)).data["title"] == "one"
    assert client.patch(issue_url(1), {"title": "uno"}, format="json").data["title"] == "uno"
    assert client.get(issue_url(99)).status_code == 404


def test_delete_is_not_allowed(ctx, make_issue) -> None:
    client, project, *_ = ctx
    make_issue(project)
    assert client.delete(issue_url(1)).status_code == 405


def test_close_and_reopen_actions(ctx, make_issue) -> None:
    client, project, *_ = ctx
    make_issue(project)
    close_url = reverse("project-issue-close", kwargs={"project_slug": "apollo", "number": 1})
    reopen_url = reverse("project-issue-reopen", kwargs={"project_slug": "apollo", "number": 1})

    closed = client.post(close_url)
    assert closed.status_code == 200
    assert closed.data["status"] == "closed" and closed.data["closed_at"] is not None

    reopened = client.post(reopen_url)
    assert reopened.status_code == 200
    assert reopened.data["status"] == "open" and reopened.data["closed_at"] is None


def test_other_projects_issues_are_invisible(
    api_client, make_user, make_project, make_issue
) -> None:
    secret = make_project(slug="secret")
    make_issue(secret)
    api_client.force_authenticate(make_user())
    assert api_client.get(issues_url("secret")).status_code == 404
    assert api_client.get(issue_url(1, "secret")).status_code == 404
    assert api_client.post(issues_url("secret"), {"title": "x"}, format="json").status_code == 404
