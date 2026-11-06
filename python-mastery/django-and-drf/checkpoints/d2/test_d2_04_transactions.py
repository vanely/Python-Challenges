"""D2.04 — a race-free numbering service, atomicity, and a tested data migration."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.operations import RunPython
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_service_numbers_issues_per_project(make_project) -> None:
    from tracker.services import create_issue

    a, b = make_project(), make_project()
    numbers = [create_issue(project=a, reporter=a.owner, title=f"a{i}").number for i in range(3)]
    assert numbers == [1, 2, 3]
    assert create_issue(project=b, reporter=b.owner, title="b").number == 1
    a.refresh_from_db()
    assert a.next_issue_number == 4


def test_service_is_atomic(make_project, monkeypatch) -> None:
    from tracker import services
    from tracker.models import Issue

    project = make_project()

    def explode(*args, **kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(Issue.objects, "create", explode)
    with pytest.raises(RuntimeError):
        services.create_issue(project=project, reporter=project.owner, title="doomed")

    project.refresh_from_db()
    assert project.next_issue_number == 1, "the counter bump must roll back with the failed insert"


def test_create_project_makes_the_owner_an_admin(make_user) -> None:
    from tracker.models import Membership
    from tracker.services import create_project

    owner = make_user()
    project = create_project(owner=owner, name="Apollo", slug="apollo")
    assert project.owner == owner
    assert project.memberships.get().user == owner
    assert project.memberships.get().role == Membership.Role.ADMIN


def test_service_sets_labels(make_project) -> None:
    from tracker.models import Label
    from tracker.services import create_issue

    project = make_project()
    bug = Label.objects.create(project=project, name="bug")
    issue = create_issue(project=project, reporter=project.owner, title="x", labels=[bug])
    assert list(issue.labels.all()) == [bug]


def test_create_view_uses_the_service(client, make_project) -> None:
    project = make_project(slug="apollo")
    project.next_issue_number = 42
    project.save()
    client.force_login(project.owner)
    response = client.post(
        reverse("tracker:issue_create", kwargs={"slug": "apollo"}), {"title": "x", "priority": 2}
    )
    assert response["Location"] == "/p/apollo/issues/42/"


def _find_backfill_migration() -> tuple[tuple[str, str], tuple[str, str]]:
    executor = MigrationExecutor(connection)
    for key, migration in executor.loader.disk_migrations.items():
        if key[0] == "tracker" and any(isinstance(op, RunPython) for op in migration.operations):
            parents = [
                p for p in executor.loader.graph.node_map[key].parents if p.key[0] == "tracker"
            ]
            return parents[0].key, key
    pytest.fail("no tracker migration with a RunPython operation found")


@pytest.mark.django_db(transaction=True)
def test_backfill_migration(make_user) -> None:
    before, target = _find_backfill_migration()
    owner = make_user()

    executor = MigrationExecutor(connection)
    executor.migrate([before])
    old_apps = executor.loader.project_state([before]).apps
    Project = old_apps.get_model("tracker", "Project")
    Issue = old_apps.get_model("tracker", "Issue")
    with_issues = Project.objects.create(name="A", slug="a", owner_id=owner.pk)
    empty = Project.objects.create(name="B", slug="b", owner_id=owner.pk)
    for n in (1, 2, 7):
        Issue.objects.create(project=with_issues, number=n, title="t", reporter_id=owner.pk)

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([target])
    new_apps = executor.loader.project_state([target]).apps
    Project = new_apps.get_model("tracker", "Project")
    assert Project.objects.get(pk=with_issues.pk).next_issue_number == 8
    assert Project.objects.get(pk=empty.pk).next_issue_number == 1

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
