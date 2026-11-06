"""D2.02 — labels, and making page cost independent of row count."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext

pytestmark = pytest.mark.django_db


def test_label_names_are_unique_per_project(make_project) -> None:
    from tracker.models import Label

    p1, p2 = make_project(), make_project()
    Label.objects.create(project=p1, name="bug")
    Label.objects.create(project=p2, name="bug")
    with pytest.raises(IntegrityError), transaction.atomic():
        Label.objects.create(project=p1, name="bug")


def test_labels_attach_to_issues(make_project, make_issue) -> None:
    from tracker.models import Label

    project = make_project()
    bug = Label.objects.create(project=project, name="bug")
    ui = Label.objects.create(project=project, name="ui")
    issue = make_issue(project, labels=[bug, ui])
    assert set(issue.labels.values_list("name", flat=True)) == {"bug", "ui"}
    assert list(bug.issues.all()) == [issue]


def _queries_for_project_page(client, make_user, make_project, make_issue, n: int) -> int:
    from tracker.models import Label

    assignee = make_user()
    project = make_project(members=(assignee,))
    labels = [Label.objects.create(project=project, name=f"l{i}") for i in range(2)]
    for _ in range(n):
        make_issue(project, assignee=assignee, labels=labels)
    client.force_login(project.owner)
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(project.get_absolute_url())
    assert response.status_code == 200
    assert "l0" in response.content.decode(), "render the labels on the project page"
    return len(ctx.captured_queries)


def test_project_page_has_no_n_plus_one(client, make_user, make_project, make_issue) -> None:
    few = _queries_for_project_page(client, make_user, make_project, make_issue, n=2)
    many = _queries_for_project_page(client, make_user, make_project, make_issue, n=20)
    assert many == few, f"2 issues took {few} queries but 20 issues took {many}"
