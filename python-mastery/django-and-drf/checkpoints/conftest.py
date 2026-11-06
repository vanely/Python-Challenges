"""Fixtures shared by every checkpoint.

Imports of your app code happen inside the fixtures, so a checkpoint for an early step
never fails just because a later step's code doesn't exist yet.
"""

import itertools
from collections.abc import Callable
from typing import Any

import pytest

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def make_user(django_user_model: Any) -> Callable[..., Any]:
    counter = itertools.count(1)

    def make(username: str | None = None, **extra: Any) -> Any:
        name = username or f"user{next(counter)}"
        return django_user_model.objects.create_user(username=name, password=PASSWORD, **extra)

    return make


@pytest.fixture
def make_project(make_user: Callable[..., Any]) -> Callable[..., Any]:
    counter = itertools.count(1)

    def make(*, owner: Any = None, members: tuple[Any, ...] = (), **fields: Any) -> Any:
        from tracker.models import Membership, Project

        n = next(counter)
        owner = owner or make_user()
        fields.setdefault("name", f"Project {n}")
        fields.setdefault("slug", f"project-{n}")
        project = Project.objects.create(owner=owner, **fields)
        Membership.objects.create(project=project, user=owner, role=Membership.Role.ADMIN)
        for member in members:
            Membership.objects.create(project=project, user=member, role=Membership.Role.MEMBER)
        return project

    return make


@pytest.fixture
def make_issue() -> Callable[..., Any]:
    """Uses your create_issue service once it exists (D2.04); before that, numbers issues itself."""

    def make(project: Any, *, reporter: Any = None, title: str = "An issue", **fields: Any) -> Any:
        from tracker.models import Issue

        reporter = reporter or project.owner
        try:
            from tracker.services import create_issue
        except ImportError:
            create_issue = None

        if create_issue is not None:
            return create_issue(project=project, reporter=reporter, title=title, **fields)

        labels = fields.pop("labels", ())
        last = Issue.objects.filter(project=project).order_by("-number").first()
        issue = Issue.objects.create(
            project=project,
            number=(last.number + 1) if last else 1,
            reporter=reporter,
            title=title,
            **fields,
        )
        if labels:
            issue.labels.set(labels)
        return issue

    return make


@pytest.fixture
def api_client() -> Any:
    from rest_framework.test import APIClient

    return APIClient()
