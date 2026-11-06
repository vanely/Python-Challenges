"""D1.06 — class-based views and editing."""

import pytest
from django.urls import resolve, reverse
from django.views.generic import DetailView, ListView, UpdateView

pytestmark = pytest.mark.django_db


def test_list_and_detail_are_generic_cbvs() -> None:
    assert issubclass(resolve("/").func.view_class, ListView)
    assert issubclass(resolve("/p/apollo/").func.view_class, DetailView)


def test_issue_update_is_an_update_view() -> None:
    match = resolve("/p/apollo/issues/3/edit/")
    assert match.url_name == "issue_update"
    assert issubclass(match.func.view_class, UpdateView)


def test_cbvs_still_require_login_and_membership(client, make_user, make_project) -> None:
    make_project(slug="apollo")
    assert client.get("/p/apollo/").status_code == 302
    client.force_login(make_user())
    assert client.get("/p/apollo/").status_code == 404


def test_member_can_edit_an_issue(client, make_user, make_project, make_issue) -> None:
    member = make_user()
    project = make_project(slug="apollo", members=(member,))
    issue = make_issue(project, title="Old title")
    client.force_login(member)
    url = reverse("tracker:issue_update", kwargs={"slug": "apollo", "number": issue.number})

    assert client.get(url).status_code == 200
    response = client.post(url, {"title": "New title", "body": "", "priority": 4})
    assert response.status_code == 302
    assert response["Location"] == issue.get_absolute_url()
    issue.refresh_from_db()
    assert issue.title == "New title" and issue.priority == 4
    assert issue.number == 1, "editing must never renumber an issue"


def test_non_member_cannot_edit(client, make_user, make_project, make_issue) -> None:
    project = make_project(slug="apollo")
    make_issue(project)
    client.force_login(make_user())
    url = reverse("tracker:issue_update", kwargs={"slug": "apollo", "number": 1})
    assert client.get(url).status_code == 404
    assert client.post(url, {"title": "hijack", "priority": 2}).status_code == 404
