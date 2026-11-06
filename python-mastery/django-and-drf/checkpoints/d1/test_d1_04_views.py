"""D1.04 — URLs, views, templates, and scoping data to the current user."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_url_names_reverse() -> None:
    assert reverse("tracker:project_list") == "/"
    assert reverse("tracker:project_detail", kwargs={"slug": "apollo"}) == "/p/apollo/"
    assert (
        reverse("tracker:issue_detail", kwargs={"slug": "apollo", "number": 7})
        == "/p/apollo/issues/7/"
    )
    assert reverse("login") == "/accounts/login/"


def test_anonymous_users_are_sent_to_login(client) -> None:
    response = client.get(reverse("tracker:project_list"))
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/?next=/")


def test_login_page_renders(client) -> None:
    response = client.get(reverse("login"))
    assert response.status_code == 200
    assert b"csrfmiddlewaretoken" in response.content


def test_project_list_shows_only_my_projects(client, make_user, make_project) -> None:
    me = make_user()
    make_project(owner=me, name="Mine")
    make_project(members=(me,), name="Shared with me")
    make_project(name="Someone else's")
    client.force_login(me)

    response = client.get(reverse("tracker:project_list"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Mine" in html and "Shared with me" in html
    assert "Someone else" not in html
    assert any(t.name == "base.html" for t in response.templates), "extend base.html"


def test_project_detail_lists_issues(client, make_project, make_issue) -> None:
    project = make_project(slug="apollo")
    make_issue(project, title="First bug")
    make_issue(project, title="Second bug")
    client.force_login(project.owner)

    response = client.get(reverse("tracker:project_detail", kwargs={"slug": "apollo"}))
    assert response.status_code == 200
    assert "First bug" in response.content.decode()
    assert "Second bug" in response.content.decode()


def test_non_members_get_404_not_403(client, make_user, make_project, make_issue) -> None:
    project = make_project(slug="secret")
    make_issue(project)
    client.force_login(make_user())

    assert client.get("/p/secret/").status_code == 404
    assert client.get("/p/secret/issues/1/").status_code == 404


def test_issue_detail(client, make_user, make_project, make_issue) -> None:
    assignee = make_user("grace")
    project = make_project(slug="apollo", members=(assignee,))
    issue = make_issue(project, title="Crash on save", body="Steps...", assignee=assignee)
    client.force_login(assignee)

    response = client.get(issue.get_absolute_url())
    assert issue.get_absolute_url() == "/p/apollo/issues/1/"
    assert response.status_code == 200
    html = response.content.decode()
    assert "Crash on save" in html and "grace" in html
    assert client.get("/p/apollo/issues/99/").status_code == 404
