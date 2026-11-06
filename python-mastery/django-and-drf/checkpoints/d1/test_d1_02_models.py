"""D1.02 — models, relationships, choices, and database-enforced invariants."""

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_project_membership_and_reverse_accessors(make_user, make_project) -> None:
    alice, bob = make_user("alice"), make_user("bob")
    project = make_project(owner=alice, members=(bob,), name="Apollo", slug="apollo")

    assert str(project) == "Apollo"
    assert set(project.members.all()) == {alice, bob}
    assert list(alice.projects.all()) == [project]
    assert list(alice.owned_projects.all()) == [project]
    assert project.memberships.get(user=alice).role == "admin"
    assert project.memberships.get(user=bob).role == "member"


def test_membership_is_unique_per_project(make_user, make_project) -> None:
    from tracker.models import Membership

    alice = make_user()
    project = make_project(owner=alice)
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(project=project, user=alice)


def test_issue_defaults_and_str(make_project) -> None:
    from tracker.models import Issue

    project = make_project()
    issue = Issue.objects.create(
        project=project, number=1, title="Fix login", reporter=project.owner
    )

    assert str(issue) == "#1 Fix login"
    assert issue.status == Issue.Status.OPEN == "open"
    assert issue.priority == Issue.Priority.NORMAL == 2
    assert issue.assignee is None
    assert issue.closed_at is None
    assert issue.created_at is not None
    assert list(project.issues.all()) == [issue]


def test_issue_number_is_unique_per_project(make_project) -> None:
    from tracker.models import Issue

    p1, p2 = make_project(), make_project()
    Issue.objects.create(project=p1, number=1, title="a", reporter=p1.owner)
    Issue.objects.create(
        project=p2, number=1, title="same number, other project", reporter=p2.owner
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Issue.objects.create(project=p1, number=1, title="dup", reporter=p1.owner)


def test_closed_at_requires_closed_status(make_project) -> None:
    from tracker.models import Issue

    project = make_project()
    with pytest.raises(IntegrityError), transaction.atomic():
        Issue.objects.create(
            project=project, number=1, title="x", reporter=project.owner, closed_at=timezone.now()
        )


def test_close_and_reopen_keep_the_invariant(make_project) -> None:
    from tracker.models import Issue

    project = make_project()
    issue = Issue.objects.create(project=project, number=1, title="x", reporter=project.owner)
    issue.close()
    issue.save()
    issue.refresh_from_db()
    assert issue.status == Issue.Status.CLOSED and issue.closed_at is not None

    issue.reopen()
    issue.save()
    issue.refresh_from_db()
    assert issue.status == Issue.Status.OPEN and issue.closed_at is None


def test_on_delete_behaviour(make_user, make_project) -> None:
    from tracker.models import Comment, Issue

    reporter, assignee = make_user(), make_user()
    project = make_project(members=(reporter, assignee))
    issue = Issue.objects.create(
        project=project, number=1, title="x", reporter=reporter, assignee=assignee
    )
    Comment.objects.create(issue=issue, author=assignee, body="on it")

    with pytest.raises(ProtectedError):
        reporter.delete()

    issue.comments.all().delete()
    assignee.delete()
    issue.refresh_from_db()
    assert issue.assignee is None

    project.delete()
    assert not Issue.objects.exists()
