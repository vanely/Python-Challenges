"""D1.03 — the admin as an internal tool."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_models_are_registered() -> None:
    from tracker.models import Comment, Issue, Project

    for model in (get_user_model(), Project, Issue, Comment):
        assert model in admin.site._registry, f"{model.__name__} is not registered in the admin"


def test_issue_admin_is_configured() -> None:
    from tracker.models import Issue

    issue_admin = admin.site._registry[Issue]
    assert "status" in issue_admin.list_filter
    assert "title" in issue_admin.search_fields
    assert issue_admin.list_select_related, "set list_select_related to avoid N+1 on the changelist"


def test_project_admin_edits_memberships_inline() -> None:
    from tracker.models import Membership, Project

    inline_models = [inline.model for inline in admin.site._registry[Project].inlines]
    assert Membership in inline_models


def test_changelists_render_for_superuser(client, make_project, make_issue) -> None:
    superuser = get_user_model().objects.create_superuser("root", "root@example.com", "pw")
    project = make_project()
    make_issue(project, title="Searchable")
    client.force_login(superuser)

    for url in (
        "/admin/tracker/project/",
        "/admin/tracker/issue/",
        "/admin/tracker/issue/?q=Searchable",
        "/admin/tracker/issue/?status__exact=open",
        f"/admin/tracker/project/{project.pk}/change/",
        "/admin/accounts/user/",
    ):
        assert client.get(url).status_code == 200, url
