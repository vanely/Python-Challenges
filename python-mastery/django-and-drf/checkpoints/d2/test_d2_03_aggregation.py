"""D2.03 — annotate vs aggregate, conditional counts, join fan-out, and subqueries."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def busy_project(make_user, make_project, make_issue):
    from tracker.models import Comment

    me = make_user("me")
    project = make_project(slug="busy", members=(me, make_user(), make_user()))
    issues = [make_issue(project, title=f"i{n}") for n in range(5)]
    for issue in issues[:2]:
        issue.close()
        issue.save()

    base = timezone.now() - timedelta(days=3)
    for day, issue in enumerate(issues[:3]):
        for k in range(2):
            c = Comment.objects.create(issue=issue, author=me, body=f"c{day}{k}")
            Comment.objects.filter(pk=c.pk).update(created_at=base + timedelta(days=day, hours=k))

    make_project(slug="other-project")
    return me, project, base + timedelta(days=2, hours=1)


def test_dashboard_counts_are_correct(client, busy_project) -> None:
    me, _, _ = busy_project
    client.force_login(me)
    response = client.get(reverse("tracker:dashboard"))
    assert response.status_code == 200

    rows = list(response.context["projects"])
    assert [p.slug for p in rows] == ["busy"], "only projects I'm a member of"
    (p,) = rows
    assert (p.open_count, p.closed_count) == (3, 2)
    assert p.member_count == 4, "owner + 3 members; a fan-out bug usually shows up here"


def test_dashboard_last_comment_uses_a_subquery(client, busy_project) -> None:
    me, _, expected_latest = busy_project
    client.force_login(me)
    (p,) = client.get(reverse("tracker:dashboard")).context["projects"]
    assert p.last_comment_at == expected_latest


def test_dashboard_query_count_is_constant(
    client, busy_project, make_project, django_assert_max_num_queries
) -> None:
    me, _, _ = busy_project
    for _ in range(5):
        make_project(members=(me,))
    client.force_login(me)
    with django_assert_max_num_queries(4):
        response = client.get(reverse("tracker:dashboard"))
        list(response.context["projects"])


def test_aggregate_returns_a_dict(busy_project) -> None:
    from django.db.models import Count

    from tracker.models import Issue

    result = Issue.objects.filter(project__slug="busy").aggregate(total=Count("id"))
    assert result == {"total": 5}
