"""R2.01 — API cost must not grow with page size."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _count(client, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx.captured_queries)


def test_issue_list_query_count_is_constant(api_client, make_user, make_project, make_issue):
    from tracker.models import Label

    def build(slug: str, n: int) -> str:
        assignee = make_user()
        project = make_project(slug=slug, members=(assignee,))
        labels = [Label.objects.create(project=project, name=f"l{i}") for i in range(3)]
        for _ in range(n):
            make_issue(project, assignee=assignee, labels=labels)
        api_client.force_authenticate(project.owner)
        return reverse("project-issue-list", kwargs={"project_slug": slug})

    few = _count(api_client, build("few", 2))
    many = _count(api_client, build("many", 20))
    assert many == few, f"2 issues: {few} queries, 20 issues: {many}"
    assert few <= 5


def test_project_list_counts_open_issues_in_sql(
    api_client, make_user, make_project, make_issue
) -> None:
    me = make_user()
    for n in range(6):
        project = make_project(owner=me)
        for _ in range(n):
            make_issue(project)
        closed = make_issue(project)
        closed.close()
        closed.save()
    api_client.force_authenticate(me)

    with CaptureQueriesContext(connection) as ctx:
        data = api_client.get(reverse("project-list")).data
    counts = sorted(p["open_issue_count"] for p in data["results"])
    assert counts == [0, 1, 2, 3, 4, 5]
    assert len(ctx.captured_queries) <= 3
