"""D2.01 — QuerySets are lazy, cached, and chainable; custom QuerySet methods."""

import pytest

pytestmark = pytest.mark.django_db


def test_building_a_queryset_runs_no_sql(django_assert_num_queries, make_project) -> None:
    from tracker.models import Issue

    project = make_project()
    with django_assert_num_queries(0):
        qs = Issue.objects.filter(project=project).exclude(status="closed").order_by("-priority")
        qs = qs.select_related("assignee")
    assert "ORDER BY" in str(qs.query)


def test_result_cache_means_one_query(django_assert_num_queries, make_project, make_issue) -> None:
    from tracker.models import Issue

    project = make_project()
    for _ in range(3):
        make_issue(project)
    qs = Issue.objects.filter(project=project)
    with django_assert_num_queries(1):
        assert len(qs) == 3
        assert [i.number for i in qs] == [i.number for i in qs]


def test_open_excludes_closed(make_project, make_issue) -> None:
    from tracker.models import Issue

    project = make_project()
    open_issue = make_issue(project, title="open")
    wip = make_issue(project, title="wip", status=Issue.Status.IN_PROGRESS)
    closed = make_issue(project, title="closed")
    closed.close()
    closed.save()

    assert set(Issue.objects.open()) == {open_issue, wip}


def test_visible_to_scopes_by_membership(make_user, make_project, make_issue) -> None:
    from tracker.models import Issue

    me = make_user()
    mine = make_issue(make_project(members=(me,)))
    make_issue(make_project())

    assert list(Issue.objects.visible_to(me)) == [mine]


def test_custom_methods_chain_in_any_order(make_user, make_project, make_issue) -> None:
    from tracker.models import Issue

    me = make_user()
    project = make_project(members=(me,))
    keep = make_issue(project)
    done = make_issue(project)
    done.close()
    done.save()

    assert list(Issue.objects.visible_to(me).open()) == [keep]
    assert list(Issue.objects.open().visible_to(me)) == [keep]
    assert list(Issue.objects.filter(project=project).open()) == [keep]
