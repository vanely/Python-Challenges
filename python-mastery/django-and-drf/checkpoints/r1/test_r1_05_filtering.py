"""R1.05 — filtering, search, ordering, and pagination."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

URL = "/api/projects/apollo/issues/"


@pytest.fixture
def client_with_issues(api_client, make_user, make_project, make_issue):
    from tracker.models import Issue, Label

    me, bob = make_user("me"), make_user("bob")
    project = make_project(owner=me, members=(bob,), slug="apollo")
    bug = Label.objects.create(project=project, name="bug")
    make_issue(project, title="Login fails", priority=4, assignee=bob, labels=[bug])
    make_issue(project, title="Typo on homepage", priority=1)
    make_issue(project, title="Slow search", priority=3, status=Issue.Status.IN_PROGRESS)
    done = make_issue(project, title="Old login bug", priority=2, labels=[bug])
    done.close()
    done.save()
    api_client.force_authenticate(me)
    return api_client


def titles(response) -> list[str]:
    assert response.status_code == 200, response.data
    return [i["title"] for i in response.data["results"]]


def test_filter_by_status_accepts_many(client_with_issues) -> None:
    got = titles(client_with_issues.get(URL, {"status": ["open", "in_progress"]}))
    assert sorted(got) == ["Login fails", "Slow search", "Typo on homepage"]


def test_filter_by_assignee_label_priority(client_with_issues) -> None:
    c = client_with_issues
    assert titles(c.get(URL, {"assignee": "bob"})) == ["Login fails"]
    assert sorted(titles(c.get(URL, {"label": "bug"}))) == ["Login fails", "Old login bug"]
    assert sorted(titles(c.get(URL, {"min_priority": 3}))) == ["Login fails", "Slow search"]


def test_search_and_ordering(client_with_issues) -> None:
    c = client_with_issues
    assert sorted(titles(c.get(URL, {"search": "login"}))) == ["Login fails", "Old login bug"]
    assert titles(c.get(URL, {"ordering": "-priority"}))[0] == "Login fails"
    assert titles(c.get(URL, {"ordering": "priority"}))[0] == "Typo on homepage"


def test_ordering_on_unlisted_field_is_ignored(client_with_issues) -> None:
    response = client_with_issues.get(URL, {"ordering": "reporter__password"})
    assert response.status_code == 200


def test_invalid_filter_value_is_a_400(client_with_issues) -> None:
    assert client_with_issues.get(URL, {"status": "nonsense"}).status_code == 400


def test_pagination(api_client, make_project, make_issue) -> None:
    project = make_project(slug="big")
    for n in range(25):
        make_issue(project, title=f"issue {n}")
    api_client.force_authenticate(project.owner)

    page1 = api_client.get(reverse("project-issue-list", kwargs={"project_slug": "big"})).data
    assert page1["count"] == 25
    assert len(page1["results"]) == 20
    assert page1["next"] is not None and page1["previous"] is None
    page2 = api_client.get(page1["next"]).data
    assert len(page2["results"]) == 5
